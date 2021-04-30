import os
import shutil
import traceback
import itertools
import plac
import sys

from cassis import *

""" 
1. Filters out documents that have five or fewer labels.
2. Converts data in CoNLL format to word and label lists.


Args:
    text (str): Text string in conll format, e.g.
        "Amy B-PER
         ADAMS I-PER
         works O
         at O
         the O
         University B-ORG
         of I-ORG
         Minnesota I-ORG
         . O"
    sep (str, optional): Column separator
        Defaults to \t

For every word in the sentence
    if belongs to entity
        write to txt
        assign label
    else
        write to txt
        assign O
"""


# these entities should be added -- see below
# Date (4068)
# Delikt (739)
# Strafe_Tatbestand (427)
# Schadensbetrag (378)
# Geständnis_ja (196)
# Ort (181)
# Strafe_Gesamtfreiheitsstrafe_Dauer (143)
# Strafe_Gesamtsatz_Dauer (81) // Strafe_Gesamtsatz_Betrag (80)

# These not: Vorstrafe_ja (178) // Vorstrafe_nein (34...)


def main(
        input_dir="/home/tschmude/PycharmProjects/smart-sentencing/examples/token-classification/Data/Original_CAS_Files",
        output_path="/home/tschmude/PycharmProjects/smart-sentencing/examples/token-classification/Data_processing_scripts/ConLL_Text_Files_unprocessed/"):
    """
    Step 1 of Preprocessing
    Iterate through cas directory, load cas or json files and convert to text files.
    :param input_dir: directory of CAS files
    :param output_path: input path of cas files or serialized json list
    :return: printed overview of entities and the covered text
    """

    # Labels that bear the same value will be counted for each document an then the whole document will be classified
    entity_types = ["Ort", "Datum",
                    "Strafe_Gesamtfreiheitsstrafe_Dauer", "Strafe_Gesamtsatz_Dauer", "Strafe_Gesamtsatz_Betrag",
                    "Strafe_Tatbestand", "Schadensbetrag",
                    "Vorstrafe_ja", "Vorstrafe_nein", "Geständnis_ja",
                    "straferhöhend_täter", "strafmildernd_täter", "Täter_Drogenbezug_ja"]  # special labels

    if not os.path.exists(input_dir):
        print(f"File not found: {input_dir}")
        sys.exit()

    # FIXME: adapt
    if os.path.exists(output_path):
        print(f"\nPrevious files found in: {output_path}")
        print("Deleting files...")
        for filename in os.listdir(output_path):
            file_path = os.path.join(output_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

    # load typesystem
    typesystem_ = load_typesystem(open("TypeSystem.xml", 'rb'))

    cas_list = []  # list to store cas objects
    file_list = []  # list to store files

    # if it's a directory: read out files and add to list
    if os.path.isdir(input_dir):
        print("Iterating CAS files. This may take a minute...")
        files = [w for w in os.scandir(input_dir)]
        for file in files:
            if ".cas.xmi" in file.name:
                with open(file, 'rb') as f:
                    try:
                        cas_list.append(load_cas_from_xmi(f, typesystem=typesystem_))
                    except KeyError:
                        print(f"KeyError at file {file}")
                    file_list.append(f.name)
                    f.close()
        find_cas_entities(output_path, cas_list, files, entity_types)


def find_cas_entities(path, cas_list, file_list, entity_types):
    """list of tuples with form ([entities], sofa string)"""

    print("Extracting tokens...")
    # filter files & extract nes from cas files
    for cas in cas_list:

        # Filter file out if less than five labels
        ne_list = []
        for ne in cas.select("de.fraunhofer.iais.kd.textmining.types.NamedEntity"):
            if ne.__getattribute__("entityType") in entity_types:
                ne_list.append(ne)
        # print Length of lists and lists
        # print(f"{len(ne_list)} ==> {[x.__getattribute__('entityType') for x in ne_list]}")
        if len(ne_list) <= 5:
            continue

        # Extraction
        tokens_labelled = []

        continue_appending = False
        ne_continue = None

        for token in cas.select("de.fraunhofer.iais.kd.textmining.types.Token"):

            begin_token = token.__getattribute__("begin")

            # if the next tokens belong to a named entity
            if continue_appending:

                # see if the token is in the corresponding passage
                span = ne_continue.get_covered_text()

                # append it with label if so, otherwise append it with O and skip to next token
                if token.get_covered_text() in span:
                    tokens_labelled.append((token.get_covered_text(), ne_continue.__getattribute__("entityType")))
                else:
                    continue_appending = False
                    tokens_labelled.append((token.get_covered_text(), "O"))
                continue

            for named_entity in cas.select("de.fraunhofer.iais.kd.textmining.types.NamedEntity"):

                if not named_entity.__getattribute__("entityType") in entity_types:
                    continue

                if begin_token == named_entity.__getattribute__("begin"):
                    tokens_labelled.append((token.get_covered_text(), named_entity.__getattribute__("entityType")))
                    ne_continue = named_entity
                    continue_appending = True
                    break

            if not continue_appending:
                tokens_labelled.append((token.get_covered_text(), "O"))

        # print(tokens_labelled)

        # write nes with labels to txt
        with open(path + file_list[cas_list.index(cas)].name.replace(".cas.xmi", ".txt"), "a", encoding="utf-8") as f:

            f.write(f"{tokens_labelled[0][0]} {tokens_labelled[0][1]}\n")  # write first element
            for previous, current in pairwise(tokens_labelled):  # then iterate through rest
                f.write(f"{current[0]} {current[1]}\n")
                if current[0] == "." and previous[0].lower() not in ["abs", "gem", "u.a", "nr", "d", "ziff", "ni"]:
                    f.write("\n")

            """for item in tokens_labelled:
                f.write(f"{item[0]} {item[1]}\n")
                if item[0] == ".":
                    print(tokens_labelled[tokens_labelled.index(item)-1][0])
                    f.write("\n")"""

    print("Done.")


def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


if __name__ == '__main__':
    plac.call(main)
