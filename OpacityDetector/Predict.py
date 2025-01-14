import glob
import os
import numpy as np
import zipfile
from collections import Counter
import tensorflow as tf
from GradientVisualiser import GradCAM
import cv2, imutils
import tqdm

def predict(model, file_path, choice,verbose=1):
    images,predictions,y_pred = [],[],[]
    if any(x in choice.lower() for x in ['resnet','1']):
        dim, channels,flag = (200, 200), 3,0
    else:
        dim, channels,flag = (400, 400), 1,1
    invalid_format_counter = 0
    for i in tqdm.tqdm(glob.glob(os.path.join(file_path,'*'))):
        if i.split('\\')[-1].split('.')[-1].lower() not in ['jpeg','jpg','png','jfif']:
            print("Invalid file format '{}' for file: {}. Supported formats: jpeg,png,jpg,jfif. Skipping current file".format(i.split('\\')[-1].split('.')[-1],i))
            invalid_format_counter +=1
            continue
        images.append(i)
        img = open(i, 'rb').read()
        img = tf.image.decode_jpeg(img, channels=channels)
        img = tf.image.resize(img, dim)
        img = img * (1. / 255)
        pred1 = model.predict(tf.expand_dims(img, axis=0))
        pred = "Negative" if pred1[0] < 0.3 else "Positive"
        if verbose==1:
            print(i, '-->', pred,pred1)
        predictions.append(pred)
        y_pred.append(pred1)
    if flag==0:
        print("COVID-Resnet: ",Counter(predictions))
    elif flag==1:
        print("Custom Model: ",Counter(predictions))
    if invalid_format_counter!=0:
        print("Skipped predictions on {} images due to invalid file formats. Please use Supported formats only(jpeg,png,jpg,jfif)".format(invalid_format_counter))
    return images,y_pred


def display(links, model, category, layer_name):
    if any(x in category.lower() for x in ['resnet','1']):
        dim, channels = (200, 200), 3
    else:
        dim, channels = (400, 400), 1
    for j in links:
        img = open(j, 'rb').read()
        image = tf.image.decode_jpeg(img, channels=channels)
        img = tf.cast(image, tf.float32) * (1. / 255)
        img = tf.image.resize(img, dim)
        img1 = tf.expand_dims(img, axis=0)
        gc = GradCAM(model, 0, layerName=layer_name)

        heatmap = gc.compute_heatmap(img1)
        heatmap = cv2.resize(heatmap, dim)

        (heatmap, output) = gc.overlay_heatmap(heatmap, image, dim=dim, channels=channels, alpha=0.5)
        if channels==1:
            image = cv2.resize(cv2.cvtColor(np.array(image), cv2.COLOR_GRAY2RGB), dim)
        else:
            image = cv2.resize(np.array(image),dim)
        output1 = np.vstack([image, output])
        output1 = imutils.resize(output1, height=700)
        cv2.startWindowThread()
        cv2.imshow(j.split('\\')[-1], output1)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def ensemble(model1,model2,file_path,verbose=0):
    links,y_pred1 = predict(model1,file_path,'resnet',verbose=verbose)
    _,y_pred2 = predict(model2,file_path,'custom',verbose=verbose)
    ensembled_result = np.mean([y_pred1,y_pred2],axis=0)
    return links,ensembled_result


if __name__ == '__main__':
    directory = str(input("Enter path to the directory which contains the images: "))
    choice = str(input("Which model to use? \n1. COVID-Resnet\n2. Custom(Recommended)\n3. Ensemble (Slower, usually more accurate)")).lower()
    verbose = str(input("Enable verbose?(Y/N)")).lower()
    verbose = 1 if verbose=='y' else 0

    if any(x in choice.lower() for x in ['resnet','1']):
        if not os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'SecondPrunedResnet.h5')):
            with zipfile.ZipFile('COVID-Resnet.zip', 'r') as zipObj:
                zipObj.extractall()
                print("Extracted model successfully")
        model_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'SecondPrunedResnet.h5')

    elif any(x in choice.lower() for x in ['custom','2']):
        model_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'OpacityDetector.h5')

    elif any(x in choice.lower() for x in ['ensemble','3']):
        if not os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'SecondPrunedResnet.h5')):
            with zipfile.ZipFile('COVID-Resnet.zip', 'r') as zipObj:
                zipObj.extractall()
                print("Extracted model successfully")
        model_path1 = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'SecondPrunedResnet.h5')
        model_path2 = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'OpacityDetector.h5')
        model1 = tf.keras.models.load_model(model_path1)
        model2 = tf.keras.models.load_model(model_path2)
        links,result = ensemble(model1,model2,file_path=directory)
        prediction = []
        for i,j in zip(links,result):
            if j<0.3:
                pred1 = "Negative"
            else:
                pred1 = "Positive"
            prediction.append(pred1)
            if verbose==1:
                print(i,"--->",j)
        print("Ensembling Results:", Counter(prediction))
        exit(0)

    else:
        print("Invalid Option")
        exit(1)

    model = tf.keras.models.load_model(model_path)
    print("Model loaded successfully")

    if not os.path.exists(directory):
        raise FileNotFoundError
    else:
        links,_ = predict(model, directory, choice.lower(),verbose=verbose)

        visualise_choice = str(input("Do you want to visualise gradients? (Y/N)")).lower()
        if visualise_choice == 'y':
            print("Press any key to view the next image")
            display(links,model,str(choice),None)
        else:
            exit(0)


# NORMAL TEST CASES
# Custom Model: Counter({'Negative': 2945, 'Positive': 56})
# Ensembling Results: Counter({'Negative': 2748, 'Positive': 253})

# COVID-19 TEST SET
# Custom Model: Counter({'Positive': 37, 'Negative': 6})
# Ensembling Results: Counter({'Positive': 41, 'Negative': 2})

# VUNO OPACITY DATA
# Custom Model: Counter({'Positive': 9, 'Negative': 3})
# Ensembling Results: Counter({'Positive': 8, 'Negative': 4})