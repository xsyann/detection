Detection
=========

Object detection using OpenCV Haar Feature-based Cascade Classifiers

![alt text](http://www.xsyann.com/epitech/detection.png)

### Install

    git clone https://github.com/xsyann/detection.git

### Usage

    python detection.py
    

### Requirements
  
    cv2, numpy, PyQt5

### Features

![alt text](http://www.xsyann.com/epitech/detection_icon.png)

**Source**

* `File` : Image / video path or url
* `Camera`

**Pre-processing**

* `Input` : Display source image
* `Pre-processed` : Display pre-processed image
* `Equalize histogram` : Equalize the source histogram before detecting

**Detect**

Select classifiers by add / removing classifiers with arrows.
Hierarchize the tree by dragging classifiers.

**Classifier display**

* `Show name`
* `Shape` : Rectangle / Ellipse
* `Transparent` : The outline of the selected shape is displayed
* `Color` : A filled shape is displayed
* `Image` : The selected image source is displayed inside the shape
* `Blur` : The shape is blurred

**Classifier parameters**

* `Stabilize` : Store detected objects when checked and try to retreive them on next frame. Allow to avoid jump between frames.
* `Tracking` : Draw lines between each previous positions of detected objects (stabilization is enabled when tracking is checked).
* `Scale factor` : How much the image size is reduced at each image scale
* `Min neighbors` : How many neighbors each candidate rectangle should have to retain it
* `Auto neighbors` : Increase `Min neighbors` until the number of detected objects is lower or equal at the selected parameter
* `Minimum Size` : Minimum possible object size. Objects smaller than that are ignored

### References

* http://note.sonots.com/SciSoftware/haartraining.html
* http://coding-robin.de/2013/07/22/train-your-own-opencv-haar-classifier.html
* http://docs.opencv.org/modules/objdetect/doc/cascade_classification.html
* http://makematics.com/research/viola-jones/
* http://docs.opencv.org/trunk/doc/py_tutorials/py_objdetect/py_face_detection/py_face_detection.html
