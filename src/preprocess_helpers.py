import re
import csv
from collections import Counter
import editdistance
import random

def split_hadm_ids(diagnosis):
    training = []
    valid = []
    test = []
    for key in diagnosis:
        num = random.random()
        if num < 0.8:
            training.append(key)
        elif num < 0.9:
            valid.append(key)
        else:
            test.append(key)
    return (training, valid, test)

# def tokenize(data):
#     for d in data:
#         if 'notes' in d:
#             new_notes = []
#             for i, note in enumerate(d['notes']):
#                 n = tokenize(note['note'])

def extract_vocab(data, threshold):
    pass

def find_closest_word(word, vocab):
    pass

def vocabify_text(data, vocab):
    pass

def replace_numbers(text):
    text = re.sub("[0-9]", "d", text)
    return text

def replace_break(text):
    text = re.sub('\\n', ' ', text).replace('  ', ' ')
    return text

function = {'replace numbers' : replace_numbers,
            'replace break'   : replace_break}

def get_diagnosis(label_path, icd_length):
    with open(label_path, 'r') as csvf:
        csvreader = csv.reader(csvf, delimiter=',', quotechar='"')
        skip_header = next(csvreader)
        icd = {}
        for row in csvreader:
            if icd.get(row[2]) is None:
                icd[row[2]] = {'labels':{'icd': [row[-1][:icd_length]], 'seq_no': [row[-2]]}, 'pat_id': row[1]}
            else:
                icd[row[2]]['labels']['icd'].append(row[-1][:icd_length])
                icd[row[2]]['labels']['seq_no'].append(row[-2])
    return icd

def get_top_diagnoses(diagnoses, num_labels):
    diagnoses_list = []
    for key in diagnoses:
        icds = diagnoses[key]['labels']['icd']
        diagnoses_list.extend(icds)
    top_diagnoses = [_[0] for _ in list(Counter(diagnoses_list).most_common(num_labels))]
    return top_diagnoses

def remove_diagnoses_not_intopK(diagnoses, top_diagnoses):
    for key in diagnoses:
        icds = diagnoses[key]['labels']['icd']
        new_icds = []
        new_seq_no = []
        for i, icd in enumerate(icds):
            if icd in top_diagnoses:
                new_icds.append(icd)
                new_seq_no.append(diagnoses[key]['labels']['seq_no'][i])
        diagnoses[key]['labels']['icd'] = new_icds
        diagnoses[key]['labels']['seq_no'] = new_seq_no
    return diagnoses

def remove_blank_examples(diagnoses):
    new_diagnoses = {}
    for key in diagnoses:
        if len(diagnoses[key]['labels']['icd']) != 0:
            new_diagnoses[key] = diagnoses[key]
    return new_diagnoses

def select_note_types(data, note_types):
    for d in data:
        if 'notes' in d:
            new_notes = []
            for note in d['notes']:
                if note['note_type'].lower() in note_types:
                    new_notes.append(note)
            d['notes'] = new_notes
    return data

def extract_subset_of_note(text, inc_history=True, diagnosis_short=True):
    text = text.lower()
    newtext = ''
    if inc_history:
        if 'history of present illness' in text and 'past medical history' in text:
            newtext+= text[text.index('history of present illness'):text.index('past medical history')]
        elif 'history of present illness' in text:
            start_idx = text.index('history of present illness')
            end_idx = min(text.index('history of present illness') + 1500, len(text))
            newtext += text[start_idx:end_idx]
    if 'final diagnosis' in text or 'discharge diagnosis' in text:
        if diagnosis_short:
            if 'final diagnosis' in text:
                start_idx = text.index('final diagnosis')
                end_idx = min(start_idx + 250, len(text))
                if '\n\n' in text[start_idx:]:
                    end_idx = text[start_idx:].index('\n\n')
                elif '.\n' in text[start_idx:]:
                    end_idx = text[start_idx:].index('.\n')
                newtext += text[start_idx:end_idx]
            if 'discharge diagnosis' in text:
                start_idx = text.index('discharge diagnosis')
                end_idx = min(start_idx + 250, len(text))
                if '\n\n' in text[start_idx:]:
                    end_idx = text[start_idx:].index('\n\n')
                elif '.\n' in text[start_idx:]:
                    end_idx = text[start_idx:].index('.\n')
                newtext += text[start_idx:end_idx]
        else:
            if 'final diagnosis' in text:
                newtext += text[text.index('final diagnosis'):]
            if 'discharge diagnosis' in text:
                newtext += text[text.index('discharge diagnosis'):]
    return newtext

def process_text(data, note_content, preprocessing):
    flag = True
    for key in data:
        if 'notes' in data[key]:
                for i, note in enumerate(data[key]['notes']):
                    if i == 0 and flag:
                        print("EXAMPLE NOTE PROCESSING...")
                        print("Original note")
                        print(note)
                        print()
                    if note_content == 1:
                        n = note['note'].lower()
                    elif note_content == 2:
                        n = extract_subset_of_note(note['note'], inc_history=False, diagnosis_short=True)
                    elif note_content == 3:
                        n = extract_subset_of_note(note['note'], inc_history=False, diagnosis_short=False)
                    elif note_content == 4:
                        n = extract_subset_of_note(note['note'], inc_history=True, diagnosis_short=False)
                    else:
                        print("Error, unrecognised preprocessing step, doing nothing")
                        n = note['note']
                    if i == 0 and flag:
                        print("Note after text selection")
                        print(n)
                        print()
                    for p in preprocessing:
                        n = function[p](n)
                    if i == 0 and flag:
                        print("Note after text processing")
                        print(n)
                        print()
                    data[key]['notes'][i]['note'] = n
                    flag = False
    return data

def build_notes(notes_path, data, note_types):
    with open(notes_path, 'r') as csvf:
        csvreader = csv.reader(csvf, delimiter=',', quotechar='"')
        skip_header = next(csvreader)
        num = 0
        num_included = 0
        for row in csvreader:
            num += 1
            if data.get(row[2]):
                # Skipping is ISERROR
                if isinstance(row[-2], int) and int(row[-2]) == 1:
                    continue
                num_included += 1
                if row[6].lower() in note_types:
                    note_dict = {"note_type": row[6],
                                "description": row[7],
                                "note": row[-1],
                                "date": row[3]
                                }
                    if data[row[2]].get('notes') is None:
                        data[row[2]]['notes'] = [note_dict]
                    else:
                        data[row[2]]['notes'].append(note_dict)
            if num % 100000 == 0:
                print("Processed {} rows".format(num))
        print("Number of HADM ID with notes added: {}".format(num_included))
    return data

def convert_format(data):
    new_data = []
    for key in data:
        datapoint = []
        if 'notes' in data[key]:
            for note in data[key]['notes']:
                if len(note['note']) > 5:
                    if len(datapoint) == 0:
                        datapoint.append(key)
                        datapoint.append(note['note'])
                        icd_str = str(" ".join([icd for icd in data[key]['labels']['icd']]))
                        datapoint.append(icd_str)
                    else:
                        datapoint[1] += ". " + note['note']
        if len(datapoint) != 0:
            new_data.append(datapoint)
    return new_data

def write_to_file(filename, data):
    f = open(filename, 'w')
    for d in data:
        f.write(d[0] + ',' + d[1] + ',' + d[2] + '\n')
    f.close()
    print("Data written to {}".format(filename))