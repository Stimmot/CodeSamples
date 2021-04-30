import logging
import subprocess
from contextlib import contextmanager
from pathlib import Path
import img2pdf
import ocrmypdf
import os
from PIL import Image
import wand.image

from utils.file_utils import get_dir


class IMGtoPDFHandler:

    def __init__(self):
        self.log = logging.getLogger('IMGtoPDFService.imgtopdfhandler')
        self.results_dir = get_dir(name='results')
        self.log.info('Created IMGtoPDFHandler')

    def get_ocr_from_img(self, source: Path):
        """Loads the image, converts it to a pdf and adds an ocr layer, returns final pdf"""
        self.log.info(f"Get pdf from image={source}")
        with self.convert_img_to_pdf(source) as pdf_file:
            # Run OCR on PDF file
            self.log.info(f"Run OCR on pdf file={pdf_file}")
            with self.get_result_file(source) as result:
                self.log.info(f"Return result={result}")
                # TODO: return file to post request?
                return f'Executed successfully'

    @contextmanager
    def convert_img_to_pdf(self, source: Path):
        """Create pdf location, call alpha channel removal, returns location of pdf"""
        pdf_loc = self.results_dir.joinpath(source.stem + ".pdf")

        self.log.info(f"Remove alpha channel from image={source}")
        img_sans_alphachannel = self.remove_alpha(source)

        self.log.info(f"From temp image create pdf={pdf_loc}")
        with open(pdf_loc, "wb") as f1, open(img_sans_alphachannel, "rb") as f2:
            f1.write(img2pdf.convert(f2))

        self.log.info(f"Delete temp image={img_sans_alphachannel}")
        if img_sans_alphachannel.is_file():
            img_sans_alphachannel.unlink()

        yield pdf_loc

    def remove_alpha(self, source):
        """Remove alpha channel and create new image with suffix _sans_alphachannel"""
        with wand.image.Image(filename=source) as img:
            img.alpha_channel = False  # close alpha channel
            img.background_color = wand.image.Color('white')
            new_source_path = self.results_dir.joinpath(source.stem + "_sans_alphachannel" + source.suffix)
            img.save(filename=new_source_path)
            self.log.info(f"Temp image without alpha channel={new_source_path}")
            return new_source_path

    @contextmanager
    def get_result_file(self, source: Path):
        """Manages the lifetime of the imgtopdf result file"""
        self.log.debug(f'get_result_file for source={source}')
        destination = self.results_dir.joinpath(source.stem + '.pdf')
        try:
            self.ocr(destination, destination)
            yield destination
        except:
            if destination.is_file():
                destination.unlink()
            raise RuntimeError('could not get result file from imgtopdf')
        else:
            self.log.debug(f'get_results_file delete={destination}')
            destination.unlink()

    def ocr(self, pdf_file, destination):
        """Calling ocrmypdf"""
        self.log.debug(f'ocr for source={pdf_file}')
        ocrmypdf.ocr(pdf_file, destination, deskew=True, language="deu", oversample=500)
