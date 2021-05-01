from numpy import array
from sklearn.model_selection import KFold
import os
import run_ner
import sys
import json
import random

def main(json_config):
    working_dir = "/home/IAIS/tschmude/bert_remote/examples/token-classification/Data_processing_scripts/CrossVal_Files/Rotation/Train_file_swap"
    train_set_directory = "/home/IAIS/tschmude/bert_remote/examples/token-classification/Data_processing_scripts/CrossVal_Files/Rotation/Train"
    test_set_directory = "/home/IAIS/tschmude/bert_remote/examples/token-classification/Data_processing_scripts/CrossVal_Files/Rotation/Test"
    test_swap_directory = "/home/IAIS/tschmude/bert_remote/examples/token-classification/Data_processing_scripts/CrossVal_Files/Rotation/Test_file_swap"
    test_pred_directory = "/home/IAIS/tschmude/bert_remote/examples/token-classification/Data_processing_scripts/CrossVal_Files/Rotation/Test_predictions"
    train_files = os.listdir(train_set_directory)
    test_files = os.listdir(test_set_directory)
    only_predict = False

    # assign training data
    data = array(train_files)
    kfold = KFold(10, False)

    # iterate through hyperparameter search
    """{
        "per_gpu_batch_size": [16, 32],
        "learning_rate": [2e-5, 3e-5, 5e-5],
        "num_epochs": [2, 3, 4]
        weight decay? "weight_decay": (0, 0.3),
        warmup steps? "warmup_steps": (0, 500),
    }"""

    if not only_predict:
        count = 0
        for train, dev in kfold.split(data):

            # only do it 5 times for now
            count += 1
            if count > 5:
                print(f"Count reached {count}.\nTerminating...")
                break

            # Epoch count
            print("\n\n*=====*")
            print(f" COUNT {count}")
            print("*=====*\n\n")

            # Training
            print("\nTraining\n")

            # set config
            with open(json_config) as json_file:
                json_data = json.load(json_file)
                json_data["do_train"] = True
                json_data["do_eval"] = True
                json_data["do_predict"] = True
                print(f"\nSet Training to True...")
            with open(json_config, "w") as json_out:
                json.dump(json_data, json_out)

            # construct text files from file splits
            string_train_body = ""
            string_dev_body = ""

            for txt_file in data[train]:
                with open(f"{train_set_directory}/{txt_file}", "r", encoding="utf-8") as f:
                    string_train_body = string_train_body + f.read()

            for txt_file in data[dev]:
                with open(f"{train_set_directory}/{txt_file}", "r", encoding="utf-8") as f:
                    string_dev_body = string_dev_body + f.read()

            # write to files that are used in the training
            print("\nWriting new training files...")

            with open(f"{working_dir}/train.txt", "w", encoding="utf-8") as whole_train_file:
                whole_train_file.write(string_train_body)

            with open(f"{working_dir}/dev.txt", "w", encoding="utf-8") as whole_dev_file:
                whole_dev_file.write(string_dev_body)

            # Print how long the files are
            print(f"\nStatistics:\n"
                  f"Length Training set: {len(string_train_body)}\n"
                  f"Length Test set: {len(string_dev_body)}\n"
                  f"Excerpt Test set:\n{string_dev_body[:100]}...")

            # Set seed in JSON
            print("\nWriting json config...")
            with open(json_config) as json_file:
                json_data = json.load(json_file)
                json_data["seed"] = random.randint(0, 200)
                print(f"\nCurrent Config:\n{json_data}\n")
            with open(json_config, "w") as json_out:
                json.dump(json_data, json_out)

            print("Running...\n")
            run_ner.main(json_config)
            print("\nTraining done.\n")
        print("!---DONE---!")

    elif only_predict:
        # Testing
        # Do documentwise prediction
        print("\n!---Testing---!\n")

        # prepare config for prediction
        with open(json_config) as json_file:
            json_data = json.load(json_file)
            json_data["do_train"] = False
            json_data["do_eval"] = False
            json_data["do_predict"] = True
            # json_data["model_name_or_path"] = model_path  # load new trained model
            json_data["data_dir"] = test_swap_directory  # set data dir to test directory with only one file in it
            print(f"\nModel Config:\n{json_data}\n")
        with open(json_config, "w") as json_out:
            json.dump(json_data, json_out)

        # iterate over directory with test documents (Rotation -> Test)
        print("Running...\n")
        for file in test_files:
            print("\n\n"
                  f">>>>>>>{file}<<<<<<<<"
                  f"\n\n")
            with open(os.path.join(test_set_directory, file), "r", encoding="utf-8") as read_file:
                test_string = read_file.read()
            with open(os.path.join(test_swap_directory, "test.txt"), "w+", encoding="utf-8") as write_file:
                write_file.write(test_string)

            result_string, pred_dict = run_ner.main(json_config)

            # construct dictionary
            entity_types = ["O",
                            "Ort", "Datum",
                            "Strafe_Gesamtfreiheitsstrafe_Dauer", "Strafe_Gesamtsatz_Dauer", "Strafe_Gesamtsatz_Betrag",
                            "Strafe_Tatbestand_Paragraph", "Strafe_Tatbestand_Beschreibung",
                            "Schadensbetrag_Beschreibung", "Schadensbetrag_Betrag",
                            "Vorstrafe_nein", "Gestaendnis_ja",
                            "straferhoehend_taeter", "strafmildernd_taeter", "Taeter_Drogenbezug_ja"]
            whole_dict = {key: {"original": [], "prediction": []} for key in entity_types}

            # populate original dict
            original_dict = {key: [] for key in entity_types}

            # Collect labels
            word_string = ""
            for previous, current in run_ner.pairwise(test_string.splitlines()):
                if not previous:
                    continue
                elif not current:
                    current = "O O"
                try:
                    old_word, old_label = previous.split()
                    new_word, new_label = current.split()
                except ValueError:
                    print("Value Error")
                    print(f"Couldn't unpack {file}")
                    print("Continuing...")
                    continue
                if old_label != "O":
                    if old_label == new_label:
                        word_string = word_string + " " + old_word if word_string else word_string + old_word
                    else:
                        word_string = word_string + " " + old_word if word_string else word_string + old_word
                        original_dict[old_label].append(word_string)
                        word_string = ""

            # put dict items in whole dictionary
            for key in whole_dict:
                whole_dict[key]["prediction"] = pred_dict[key]
                whole_dict[key]["original"] = original_dict[key]

            with open(os.path.join(test_pred_directory, file), "w+", encoding="utf-8") as write_file:
                write_file.write("===> " + file)
                write_file.write(result_string + "\n")

                # scan trough dict, make pretty and assign simple labels
                for key in whole_dict:
                    write_file.write(f"{key}:\n")
                    write_file.write(f"\tOriginal:\n")
                    for item in whole_dict[key]['original']:
                        write_file.write(f"\t   \"{item}\"\n")
                    write_file.write(f"\tPrediction:\n")
                    for item in whole_dict[key]['prediction']:
                        write_file.write(f"\t   \"{item}\"\n")
                    write_file.write("\n\n")

        print("\nPredictions done.\n")

            # let ner predict test file
            # take results and predictions and save it under file name in Test predictions
            # for each binary/document-wise label:
                # go through test document, collect labels
                # then go through predictions, collect labels
                # save and print for easy comparison

        # set config to eval & test (only do train before)
        # load trained model
        # iterate over directory with test documents (Rotation -> Test)
        # let eval & predict on every document
        # go through doc, fill a parameters dictionary (Gesamtfreiheitsstrafe, Drogen, etc.) with predictions
        # print parameters dictionary below evaluation, check against original documents by scanning through them
        # with simple regex patterns and writing it like "Original Doc: Drogenbezug_ja; Prediction: Drogenbezug_ja"
        # or simply with True, Fals or NaN for binary parameters and discrete values for numerical parameters

        print("!---DONE---!")


if __name__ == "__main__":
    main(sys.argv[1])
