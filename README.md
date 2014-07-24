Detection
=========

Object detection using OpenCV Haar Feature-based Cascade Classifiers

![screen](http://www.xsyann.com/epitech/detection.png)

### Install

    git clone https://github.com/xsyann/detection.git

### Usage

    python detection.py
    

### Requirements
  
    cv2, numpy, PyQt5

### Features

![icon](http://www.xsyann.com/epitech/detection_icon.png)

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


### More

#### Méthode de Viola et Jones

La méthode de Viola et Jones consiste à entrainer une fonction à reconnaitre si un objet est présent ou non dans une zone de l’image.

**Entrainement**

L’algorithme d’entrainement nécessite une importante quantité d’images positives (contenant l’objet) et négatives (ne contenant pas l’objet). Le but est d'extraire des caractéristiques à partir de ces images.
Les caractéristiques, appelées caractéristiques pseudo-Haar, représentent la différence de sommes de pixels de plusieurs zones rectangulaires adjacentes.

Voici les types de base de caractéristiques utilisés par OpenCV :

![haar](http://docs.opencv.org/_images/haarfeatures.png)

Une caractéristique correspond donc à un nombre obtenu par la soustraction de la somme des pixels sous les rectangles blancs et de la somme des pixels sous les rectangles noirs. Cela permet de comparer l’intensité lumineuse moyenne des zones blanches et noires.

![haar](http://docs.opencv.org/trunk/_images/haar.png)

Chaque type de base peut être décliné en combinant différentes largeurs / hauteurs / positions. Pour une image de 24x24 cela représente plus de 160000 caractéristiques possibles (cf. doc OpenCV).
Certaines caractéristiques sont plus intéressantes que d’autres comme par exemple les deux ci-dessus. La première permet de comparer la région des yeux (sombre) avec la région des joues et du nez (plus claire). La seconde permet de comparer les yeux (sombre) avec l’arrête du nez (plus claire).

Il s’agit, pour chaque caractéristique, de trouver le seuil qui classe le plus d’images correctement. Les caractéristiques avec le taux d’erreurs le plus bas sont alors sélectionnées et sont appelées classifieurs “faibles”. Un classifieur est considéré comme faible à partir du moment où il possède un taux d’erreur inférieur à un classifieur aléatoire.
Un classifieur faible ne peut pas classifier tout seul une image, mais un ensemble de classifieurs faibles (pondérés) le peut et est alors appelé classifieur “fort”.

Cependant, appliquer les classifieurs à chaque zone de l’image pour détecter la présence d’un objet n’est pas très efficace étant donné que la plupart des zones de l’image ne contiennent pas cet objet.
C’est pour cela qu’a été introduit le concept de cascades. Les cascades permettent de détecter l’absence d’un objet et donc d’éliminer rapidement une zone inintéressante.
En effet, les cascades groupent les classifieurs en différentes étapes ; à chaque étape, si la zone est classée negative, cette dernière est éliminée, sinon l’étape suivante est calculée.
Cela permet d’écarter une image négative dès qu’une étape n’est pas validée et de garder une image positive seulement si toutes les étapes sont validées.

*Exemple:*

    Etape 1 : 1 classifieur   
    Etape 2 : 10 classifieurs
    Etape 3 : 25 classifieurs
    Etape 4 : 25 classifieurs
    Etape 5 : 50 classifieurs
    ...

**Optimisations**

Les sommes de pixels sont calculées très rapidement grâce aux images intégrales.

Une image intégrale est une image dans laquelle chaque pixel contient la somme des pixels à gauche et au-dessus de lui.
Ainsi pour une caractéristique à deux rectangles il suffit d’accéder à seulement six pixels de l’image intégrale pour calculer la différence des sommes des pixels.

**Détection** 

Une fenêtre de détection de petite taille est définie (par exemple 20x20). La cascade de classifieurs détecte si un objet est présent dans cette zone. À chaque itération la fenêtre de détection est décalé d’un pixel (ou plus), afin de balayer toute l’image. Une fois balayée, la fenêtre de détection est agrandie (ou l’image réduite, suivant l’implémentation), et le processus est recommencé afin de tester des zones de toutes tailles.

Le fait de tester des zones de toutes tailles et positions induit le fait que le même objet peut être détecté dans plusieurs zones. Les zones se chevauchant sont regroupées en une zone "moyenne".
Il est possible de définir un nombre minimal de zones se chevauchant au-dessus duquel l'objet est considéré comme détecté, afin d'éliminer les faux positifs.

http://vimeo.com/12774628

#### Égalisation d’histogramme

Un histogramme est la représentation graphique de la distribution des intensités d’une image.
L’égalisation d’histogramme sert à augmenter le contraste en répartissant mieux les intensités.
Graphiquement cela revient à "étaler" l’histogramme.

![histo](http://docs.opencv.org/_images/Histogram_Equalization_Theory_1.jpg)

#### Stabilisation

Le but étant de retrouver, dans l’image courante, les objets détectés dans l’image précédente.

Si un objet de l’image précédente n’est pas associé à un objet de l’image courante, il est laissé à la même position.
Pour chaque objet précédent il s’agit de trouver l’objet de l’image courante le plus près de lui qui ne soit pas plus près d’un autre objet de l’image précédente.

*Algorithme simplifié :*

    for prev in previous:
	    obj = retreiveObject(prev)

    def retreiveObject(prev):
	    nearestCurrent = getNearest(from=prev, in=current)
	    nearestPrev = None
	    while previousObjects.notEmpty() and nearestCurrent:
		    nearestPrev = getNearest(from=nearestCurrent, in=previousObjects)
		    if nearestPrev != prev:
			    previousObjects.remove(nearestPrev)
			    currentObjects.remove(nearestCurrent)
			    nearestCurrent = getNearest(from=prev, in=currentObjects)
		    else:
			    break
			
	    return nearestCurrent
	

#### Entrainement

1. Regrouper les chemins de fichiers des images positives et negatives

    `find ./positives -iname "*.jpg" > positives.txt`
    `find ./negatives -iname "*.jpg" > negatives.txt`

2. Créer des échantillons à partir des images positives

    `opencv_createsamples` permet de créer des échantillons en combinant une image positive déformée et des images negatives.
    Le script `createsamples.pl` permet de répéter l’operation pour chaque image positive afin d’atteindre le nombre d’échantillons passé en paramètre.

    `perl bin/createsamples.pl positives.txt negatives.txt samples 2000 "opencv_createsamples -bgcolor 0 -bgthresh 0 -maxxangle 1.1 -maxyangle 1.1 maxzangle 0.5 -maxidev 40 -w 25 -h 24"`

    Le format de sortie est un format de description qui contient le contenu des images suivi du nombre d’objets présents dedans, ainsi que leurs positions dans l’image.

3. Regrouper les échantillons dans un fichier

    `find ./samples -name '*.vec' > samples.txt`
    
    `./bin/mergevec samples.txt samples.vec`

4. Entrainer

    `opencv_traincascade -data classifier -vec samples.vec -bg negatives.txt -numStages 12 -minHitRate 0.999 -maxFalseAlarmRate 0.5 -numPos 1800 -numNeg 1200 -w 25 -h 24 -mode ALL -precalcValBufSize 1024 -precalcIdxBufSize 1024 -featureType LBP`

    * `numStages` : Nombre d’étape dans la cascade
    * `minHitRate` : Taux minimal de bonne classification
    * `minFalseAlarmRate` : Taux minimal de faux positif par étape
    * `featureType` : Pseudo-Haar ou Motif binaire local (LBP)

#### Informations

Pour compiler OpenCV avec le support "Threading Building Blocks" pour profiter pleinement de la puissance de tous les coeurs du processeur.

    $ cd opencv
    $ mkdir build
    $ cd build
    $ cmake -D WITH_TBB=ON
    $ make -j8
    $ sudo make install
