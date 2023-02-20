##################################################################
# 모델로 검지한 bbox와 xml bndbox 차이로 검수
# 9000장 까지만 가능(1TB미만)
##################################################################

import os
import cv2
import numpy as np
import torch
from torch import nn
from torch.autograd import Variable


def parse_xml_annotations(xml_file):
    # Parses the XML annotations from the xml file and returns a list of annotations(Object class label, bndbox)

    # Initialize list to store annotations
    annotations = []

    # Parse XML file and extract object annotations
    for line in xml_file:
        # Split line into words
        words = line.strip().split()

        # Check if line contains object annotation
        if len(words) == 4:
            class_label = int(words[0])
            xmin = int(words[1])
            ymin = int(words[2])
            xmax = int(words[3])
            ymax = int(words[4])
            annotations.append((class_label, xmin, ymin, xmax, ymax))

    return annotations

def compare_predictions_with_annotations(predictions, xml_annotations):
    # predict bbox와 xml bndbox 비교

    # Convert predictions to numpy array
    predictions = predictions.cpu().numpy() #cpu
    #predictions = predictions.numpy() #gpu -> error

    # Loop over objects in the image
    for i, annotation in enumerate(xml_annotations):
        class_label = annotation[0]
        xmin = annotation[1]
        ymin = annotation[2]
        xmax = annotation[3]
        ymax = annotation[4]

        # Get prediction for current object
        prediction = predictions[0, class_label, i, :]

        # Check if prediction matches xml bndbox
        if abs(prediction[0] - xmin) > 5 or abs(prediction[1] - ymin) > 5 or abs(prediction[2] - xmax) > 5 or abs(prediction[3] - ymax) > 5:
            return False

    return True

if __name__ == '__main__':
    # Load YOLOv5 custom trained model
    model = torch.hub.load('ultralytics/yolov5', 'custom', path='E:/LPR_교정/모델/E/lpr_ocr_E_230130.pt', force_reload=True)
    #checkpoint = torch.load("E:/LPR_교정/모델/E/lpr_ocr_E_230130.pt", map_location='gpu')
    #model.load_state_dict(checkpoint['model'])
    model.eval()

    # Prepare image datasets
    images_folder = "E:/LPR_교정/Class_E/images/test"
    img_files = [f for f in os.listdir(images_folder) if f.endswith('.jpg')]
    num_images = len(img_files)
    images = []
    for filename in img_files:
        image = cv2.imread(os.path.join(images_folder, filename))
        images.append(image)

    # Load XML datasets
    xml_folder = "E:/LPR_교정/Class_E/labels/test"
    xml_files = [f for f in os.listdir(xml_folder) if f.endswith('.xml')]
    num_xml = len(xml_files)
    xmls = []
    for filename in xml_files:
        xml_file = open(os.path.join(xml_folder, filename), "r")
        xmls.append(xml_file)

    # Extract incorrectly labeled image and XML datasets
    incorrect_images = []
    incorrect_xmls = []
    for i in range(num_images):
        image = images[i]
        xml_file = xml_files[i]

        # Preprocess image
        image = cv2.resize(image, (256, 256))
        image = image / 255.0
        image = np.transpose(image, (2, 0, 1))
        image = torch.from_numpy(image)
        image = image.unsqueeze(0)
        image = image.float()

        # Use YOLOv5 model to generate predictions
        image = Variable(image)
        outputs = model(image)

        # Extract predictions and compare with XML annotations
        predictions = outputs.data
        xml_annotations = parse_xml_annotations(xml_file)
        if not compare_predictions_with_annotations(predictions, xml_annotations):
            incorrect_images.append(images[i])
            incorrect_xmls.append(xml_files[i])

    # Store incorrectly labeled image and XML datasets
   # np.save("incorrect_images.npy", np.array(incorrect_images))
   # np.save("incorrect_xmls.npy", np.array(incorrect_xmls))
    np.savetxt("incorrect_images.txt", np.array(incorrect_images), delimiter=',', newline='n', encoding='utf-8')
    np.savetxt("incorrect_xmls.txt", np.array(incorrect_xmls), delimiter=',', 	newline='n', encoding='utf-8')