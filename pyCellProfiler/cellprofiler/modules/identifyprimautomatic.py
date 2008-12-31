"""IdentifyPrimAutomatic - identify objects by thresholding and contouring

"""
__version__="$Revision: 1$"

import cellprofiler.cpmodule
import cellprofiler.variable as cpv
from cellprofiler.cpmath.otsu import otsu
import cellprofiler.objects
from cellprofiler.variable import AUTOMATIC
import scipy.ndimage
import matplotlib.backends.backend_wxagg
import matplotlib.figure
import matplotlib.cm
import numpy
import wx

IMAGE_NAME_VAR                  = 1
OBJECT_NAME_VAR                 = 2
SIZE_RANGE_VAR                  = 3
EXCLUDE_SIZE_VAR                = 4
MERGE_CHOICE_VAR                = 5
EXCLUDE_BORDER_OBJECTS_VAR      = 6
THRESHOLD_METHOD_VAR            = 7
TM_OTSU                         = "Otsu"
TM_OTSU_GLOBAL                  = "Otsu Global"
TM_OTSU_ADAPTIVE                = "Otsu Adaptive"
TM_OTSU_PER_OBJECT              = "Otsu PerObject"
TM_MOG                          = "MoG"
TM_MOG_GLOBAL                   = "MoG Global"
TM_MOG_ADAPTIVE                 = "MoG Adaptive"
TM_MOG_PER_OBJECT               = "MoG PerObject"
TM_BACKGROUND                   = "Background"
TM_BACKGROUND_GLOBAL            = "Background Global"
TM_BACKGROUND_ADAPTIVE          = "Background Adaptive"
TM_BACKGROUND_PER_OBJECT        = "Background PerObject"
TM_ROBUST                       = "Robust"
TM_ROBUST_BACKGROUND_GLOBAL     = "RobustBackground Global"
TM_ROBUST_BACKGROUND_ADAPTIVE   = "RobustBackground Adaptive"
TM_ROBUST_BACKGROUND_PER_OBJECT = "RobustBackground PerObject"
TM_RIDLER_CALVARD               = "RidlerCalvard"
TM_RIDLER_CALVARD_GLOBAL        = "RidlerCalvard Global"
TM_RIDLER_CALVARD_ADAPTIVE      = "RidlerCalvard Adaptive"
TM_RIDLER_CALVARD_PER_OBJECT    = "RidlerCalvard PerObject"
TM_KAPUR                        = "Kapur"
TM_KAPUR_GLOBAL                 = "Kapur Global"
TM_KAPUR_ADAPTIVE               = "Kapur Adaptive"
TM_KAPUR_PER_OBJECT             = "Kapur PerObject"
TM_ALL                          = "All"
TM_SET_INTERACTIVELY            = "Set interactively"
TM_GLOBAL                       = "Global"
TM_ADAPTIVE                     = "Adaptive"
TM_PER_OBJECT                   = "PerObject"
THRESHOLD_CORRECTION_VAR        = 8
THRESHOLD_RANGE_VAR             = 9
OBJECT_FRACTION_VAR             = 10
UNCLUMP_METHOD_VAR              = 11
UN_INTENSITY                    = "Intensity"
UN_SHAPE                        = "Shape"
UN_MANUAL                       = "Manual"
UN_MANUAL_FOR_ID_SECONDARY      = "Manual_for_IdSecondary"
UN_NONE                         = "None"
WATERSHED_VAR                   = 12
WA_INTENSITY                    = "Intensity"
WA_DISTANCE                     = "Distance"
WA_NONE                         = "None"
SMOOTHING_SIZE_VAR              = 13
MAXIMA_SUPPRESSION_SIZE_VAR     = 14
LOW_RES_MAXIMA_VAR              = 15
SAVE_OUTLINES_VAR               = 16
FILL_HOLES_OPTION_VAR           = 17
TEST_MODE_VAR                   = 18
AUTOMATIC_SMOOTHING_VAR         = 19
AUTOMATIC_MAXIMA_SUPPRESSION    = 20


class IdentifyPrimAutomatic(cellprofiler.cpmodule.AbstractModule):
    """Cut and paste this in order to get started writing a module
    """
    def __init__(self):
        cellprofiler.cpmodule.AbstractModule.__init__(self)
        self.set_module_name("IdentifyPrimAutomatic")
        self.image_name = cpv.NameSubscriber('What did you call the images you want to process?', 'imagegroup')
        self.object_name = cpv.NameProvider('What do you want to call the objects identified by this module?', 'objectgroup', 'Nuclei')
        self.size_range = cpv.IntegerRange('Typical diameter of objects, in pixel units (Min,Max):', 
                                           (10,40),minval=1)
        self.exclude_size = cpv.Binary('Discard objects outside the diameter range?', True)
        self.merge_objects = cpv.Binary('Try to merge too small objects with nearby larger objects?', False)
        self.exclude_border_objects = cpv.Binary('Discard objects touching the border of the image?', True)
        self.threshold_method = cpv.Choice('''Select an automatic thresholding method or enter an absolute threshold in the range [0,1].  To choose a binary image, select "Other" and type its name.  Choosing 'All' will use the Otsu Global method to calculate a single threshold for the entire image group. The other methods calculate a threshold for each image individually. "Set interactively" will allow you to manually adjust the threshold during the first cycle to determine what will work well.''',
                                           [TM_OTSU_GLOBAL,TM_OTSU_ADAPTIVE,TM_OTSU_PER_OBJECT,
                                            TM_MOG_GLOBAL,TM_MOG_ADAPTIVE,TM_MOG_PER_OBJECT,
                                            TM_BACKGROUND_GLOBAL, TM_BACKGROUND_ADAPTIVE, TM_BACKGROUND_PER_OBJECT,
                                            TM_ROBUST_BACKGROUND_GLOBAL, TM_ROBUST_BACKGROUND_ADAPTIVE, TM_ROBUST_BACKGROUND_PER_OBJECT,
                                            TM_RIDLER_CALVARD_GLOBAL, TM_RIDLER_CALVARD_ADAPTIVE, TM_RIDLER_CALVARD_PER_OBJECT,
                                            TM_KAPUR_GLOBAL,TM_KAPUR_ADAPTIVE,TM_KAPUR_PER_OBJECT,
                                            TM_ALL,TM_SET_INTERACTIVELY])
        self.threshold_correction_factor = cpv.Float('Threshold correction factor', 1)
        self.threshold_range = cpv.FloatRange('Lower and upper bounds on threshold, in the range [0,1]', (0,1),minval=0,maxval=1)
        self.object_fraction = cpv.CustomChoice('For MoG thresholding, what is the approximate fraction of image covered by objects?',
                                                ['0.01','0.1','0.2','0.3','0.4','0.5','0.6','0.7','0.8','0.9','0.99'])
        self.unclump_method = cpv.Choice('Method to distinguish clumped objects (see help for details):', 
                                          [UN_INTENSITY, UN_SHAPE, UN_MANUAL, UN_MANUAL_FOR_ID_SECONDARY, UN_NONE])
        self.watershed_method = cpv.Choice('Method to draw dividing lines between clumped objects (see help for details):', 
                                           [WA_INTENSITY,WA_DISTANCE,WA_NONE])
        self.automatic_smoothing = cpv.Binary('Automatically calculate size of smoothing filter when separating clumped objects',True)
        self.smoothing_filter_size = cpv.Integer('Size of smoothing filter, in pixel units (if you are distinguishing between clumped objects). Enter 0 for low resolution images with small objects (~< 5 pixel diameter) to prevent any image smoothing.', 10)
        self.automatic_suppression = cpv.Binary('Automatically calculate minimum size of local maxima for clumped objects',True)
        self.maxima_suppression_size = cpv.Integer( 'Suppress local maxima within this distance, (a positive integer, in pixel units) (if you are distinguishing between clumped objects)', 7)
        self.low_res_maxima = cpv.Binary('Speed up by using lower-resolution image to find local maxima?  (if you are distinguishing between clumped objects)', True)
        self.save_outlines = cpv.NameProvider('What do you want to call the outlines of the identified objects (optional)?', 'outlinegroup', cellprofiler.variable.DO_NOT_USE)
        self.fill_holes = cpv.Binary('Do you want to fill holes in identified objects?', True)
        self.test_mode = cpv.Binary('Do you want to run in test mode where each method for distinguishing clumped objects is compared?', True)

    def variables(self):
        return [self.image_name,self.object_name,self.size_range, \
                self.exclude_size, self.merge_objects, \
                self.exclude_border_objects, self.threshold_method, \
                self.threshold_correction_factor, self.threshold_range, \
                self.object_fraction, self.unclump_method, \
                self.watershed_method, self.smoothing_filter_size, \
                self.maxima_suppression_size, self.low_res_maxima, \
                self.save_outlines, self.fill_holes, self.test_mode, \
                self.automatic_smoothing, self.automatic_suppression ]
    
    def visible_variables(self):
        vv = [self.image_name,self.object_name,self.size_range, \
                self.exclude_size, self.merge_objects, \
                self.exclude_border_objects, self.threshold_method, \
                self.threshold_correction_factor, self.threshold_range, \
                self.object_fraction, self.unclump_method ]
        if self.unclump_method != UN_NONE:
            vv += [self.watershed_method, self.automatic_smoothing]
            if not self.automatic_smoothing:
                vv += [self.smoothing_filter_size]
            vv += [self.automatic_suppression]
            if not self.automatic_suppression:
                vv += [self.maxima_suppression_size]
            vv += [self.low_res_maxima, self.save_outlines, self.fill_holes]
            vv += [self.test_mode]
        return vv

    def upgrade_module_from_revision(self,variable_revision_number):
        """Possibly rewrite the variables in the module to upgrade it to its current revision number
        
        """
        if variable_revision_number == 12:
            # Laplace values removed - propagate variable values to fill the gap
            for i in range(17,20):
                self.variable(i-1).value = str(self.variable(i))
            if self.variable(SMOOTHING_SIZE_VAR).value == cpv.AUTOMATIC:
                self.variable(AUTOMATIC_SMOOTHING_VAR).value = cpv.YES
                self.variable(SMOOTHING_SIZE_VAR).value = "10"
            else:
                self.variable(AUTOMATIC_SMOOTHING_VAR).value = cpv.NO
            variable_revision_number = 13
        if variable_revision_number != self.variable_revision_number():
            raise ValueError("Unable to rewrite variables from revision # %d"%(variable_revision_number))
    
    variable_revision_number = 13

    def category(self):
        return "Object Processing"
    
    def get_help(self):
        """Return help text for the module
        
        """
        return """This module identifies primary objects (e.g. nuclei) in grayscale images
that show bright objects on a dark background. The module has many
options which vary in terms of speed and sophistication. The objects that
are found are displayed with arbitrary colors - the colors do not mean 
anything but simply help you to tell various objects apart. You can 
change the colormap in File > Set Preferences.
%
Requirements for the images to be fed into this module:
* If the objects are dark on a light background, they must first be
inverted using the Invert Intensity module.
* If you are working with color images, they must first be converted to
grayscale using the Color To Gray module.
%
Overview of the strategy ('Settings' below has more details):
  Properly identifying primary objects (nuclei) that are well-dispersed,
non-confluent, and bright relative to the background is straightforward
by applying a simple threshold to the image. This is fast but usually
fails when nuclei are touching. In CellProfiler, several automatic
thresholding methods are available, including global and adaptive, using
Otsu's (Otsu, 1979) and our own version of a Mixture of Gaussians
algorithm (O. Friman, unpublished). For most biological images, at least
some nuclei are touching, so CellProfiler contains a novel modular
three-step strategy based on previously published algorithms (Malpica et
al., 1997; Meyer and Beucher, 1990; Ortiz de Solorzano et al., 1999;
Wahlby, 2003; Wahlby et al., 2004). Choosing different options for each
of these three steps allows CellProfiler to flexibly analyze a variety of
different cell types. Here are the three steps:
  In step 1, CellProfiler determines whether an object is an individual
nucleus or two or more clumped nuclei. This determination can be
accomplished in two ways, depending on the cell type: When nuclei are
bright in the middle and dimmer towards the edges (the most common case),
identifying local maxima in the smoothed intensity image works well
(Intensity option). When nuclei are quite round, identifying local maxima
in the distance-transformed thresholded image (where each pixel gets a
value equal to the distance to the nearest pixel below a certain
threshold) works well (Shape option). For quick processing where cells
are well-dispersed, you can choose to make no attempt to separate clumped
objects.
  In step 2, the edges of nuclei are identified. For nuclei within the
image that do not appear to touch, the edges are easily determined using
thresholding. For nuclei that do appear to touch, there are two options
for finding the edges of clumped nuclei. Where the dividing lines tend to
be dimmer than the remainder of the nucleus (the most common case), the
Intensity option works best (already identified nuclear markers are
starting points for a watershed algorithm (Vincent and Soille, 1991)
applied to the original image). When no dim dividing lines exist, the
Distance option places the dividing line at a point between the two
nuclei determined by their shape (the distance-transformed thresholded
image is used for the watershed algorithm). In other words, the dividing
line is usually placed where indentations occur along the edge of the
clumped nuclei.
  In step 3, some identified nuclei are discarded or merged together if
the user chooses. Incomplete nuclei touching the border of the image can
be discarded. Objects smaller than a user-specified size range, which are
likely to be fragments of real nuclei, can be discarded. Alternately, any
of these small objects that touch a valid nucleus can be merged together
based on a set of heuristic rules; for example similarity in intensity
and statistics of the two objects. A separate module,
FilterByObjectMeasurement, further refines the identified nuclei, if
desired, by excluding objects that are a particular size, shape,
intensity, or texture. This refining step could eventually be extended to
include other quality-control filters, e.g. a second watershed on the
distance transformed image to break up remaining clusters (Wahlby et al.,
2004).
%
For more details, see the Settings section below and also the notation
within the code itself (Developer's version).
%
Malpica, N., de Solorzano, C. O., Vaquero, J. J., Santos, A., Vallcorba,
I., Garcia-Sagredo, J. M., and del Pozo, F. (1997). Applying watershed
algorithms to the segmentation of clustered nuclei. Cytometry 28,
289-297.
Meyer, F., and Beucher, S. (1990). Morphological segmentation. J Visual
Communication and Image Representation 1, 21-46.
Ortiz de Solorzano, C., Rodriguez, E. G., Jones, A., Pinkel, D., Gray, J.
W., Sudar, D., and Lockett, S. J. (1999). Segmentation of confocal
microscope images of cell nuclei in thick tissue sections. Journal of
Microscopy-Oxford 193, 212-226.
Wahlby, C. (2003) Algorithms for applied digital image cytometry, Ph.D.,
Uppsala University, Uppsala.
Wahlby, C., Sintorn, I. M., Erlandsson, F., Borgefors, G., and Bengtsson,
E. (2004). Combining intensity, edge and shape information for 2D and 3D
segmentation of cell nuclei in tissue sections. J Microsc 215, 67-76.
%
Settings:
%
Typical diameter of objects, in pixel units (Min,Max):
This is a very important parameter which tells the module what you are
looking for. Most options within this module use this estimate of the
size range of the objects in order to distinguish them from noise in the
image. For example, for some of the identification methods, the smoothing
applied to the image is based on the minimum size of the objects. A comma
should be placed between the minimum and the maximum diameters. The units
here are pixels so that it is easy to zoom in on objects and determine
typical diameters. To measure distances easily, use the CellProfiler
Image Tool, 'ShowOrHidePixelData', in any open window. Once this tool is
activated, you can draw a line across objects in your image and the
length of the line will be shown in pixel units. Note that for non-round
objects, the diameter here is actually the 'equivalent diameter', meaning
the diameter of a circle with the same area as the object.
%
Discard objects outside the diameter range:
You can choose to discard objects outside the specified range of
diameters. This allows you to exclude small objects (e.g. dust, noise,
and debris) or large objects (e.g. clumps) if desired. See also the
FilterByObjectMeasurement module to further discard objects based on some
other measurement. During processing, the window for this module will
show that objects outlined in green were acceptable, objects outlined in
red were discarded based on their size, and objects outlined in yellow
were discarded because they touch the border.
%
Try to merge 'too small' objects with nearby larger objects:
Use caution when choosing 'Yes' for this option! This is an experimental
functionality that takes objects that were discarded because they were
smaller than the specified Minimum diameter and tries to merge them with
other surrounding objects. This is helpful in cases when an object was
incorrectly split into two objects, one of which is actually just a tiny
piece of the larger object. However, this could be dangerous if you have
selected poor settings which produce many tiny objects - the module
will take a very long time and you will not realize that it is because
the tiny objects are being merged. It is therefore a good idea to run the
module first without merging objects to make sure the settings are
reasonably effective.
%
Discard objects touching the border of the image:
You can choose to discard objects that touch the border of the image.
This is useful in cases when you do not want to make measurements of
objects that are not fully within the field of view (because, for
example, the area would not be accurate).
%
Select automatic thresholding method:
   The threshold affects the stringency of the lines between the objects
and the background. You can have the threshold automatically calculated
using several methods, or you can enter an absolute number between 0 and
1 for the threshold (to see the pixel intensities for your images in the
appropriate range of 0 to 1, use the CellProfiler Image Tool,
'ShowOrHidePixelData', in a window showing your image). There are
advantages either way. An absolute number treats every image identically,
but is not robust to slight changes in lighting/staining conditions
between images. An automatically calculated threshold adapts to changes
in lighting/staining conditions between images and is usually more
robust/accurate, but it can occasionally produce a poor threshold for
unusual/artifactual images. It also takes a small amount of time to
calculate.
   The threshold which is used for each image is recorded as a
measurement in the output file, so if you find unusual measurements from
one of your images, you might check whether the automatically calculated
threshold was unusually high or low compared to the other images.
   There are five methods for finding thresholds automatically, Otsu's
method, the Mixture of Gaussian (MoG) method, the Background method, the
Robust Background method and the Ridler-Calvard method. 
** The Otsu method
uses our version of the Matlab function graythresh (the code is in the
CellProfiler subfunction CPthreshold). Our modifications include taking
into account the max and min values in the image and log-transforming the
image prior to calculating the threshold. Otsu's method is probably best
if you don't know anything about the image, or if the percent of the
image covered by objects varies substantially from image to image. If you
know the object coverage percentage and it does not vary much from image
to image, the MoG can be better, especially if the coverage percentage is
not near 50%. Note, however, that the MoG function is experimental and
has not been thoroughly validated. 
** The Background method 
is simple and appropriate for images in which most of the image is 
background. It finds the mode of the histogram of the image, which is 
assumed to be the background of the image, and chooses a threshold at 
twice that value (which you can adjust with a Threshold Correction Factor,
see below).  Note that the mode is protected from a high number of 
saturated pixels by only counting pixels < 0.95. This can be very helpful,
for example, if your images vary in overall brightness but the objects of 
interest are always twice (or actually, any constant) as bright as the 
background of the image. 
** The Robust background
method trims the brightest and dimmest 5of pixel intensities off first
in the hopes that the remaining pixels represent a gaussian of intensity
values that are mostly background pixels. It then calculates the mean and
standard deviation of the remaining pixels and calculates the threshold
as the mean + 2 times the standard deviation. 
** The Ridler-Calvard method
is simple and its results are often very similar to Otsu's - according to
Sezgin and Sankur's paper (Journal of Electronic Imaging 2004), Otsu's 
overall quality on testing 40 nondestructive testing images is slightly 
better than Ridler's (Average error - Otsu: 0.318, Ridler: 0.401). 
It chooses an initial threshold, and then iteratively calculates the next 
one by taking the mean of the average intensities of the background and 
foreground pixels determined by the first threshold, repeating this until 
the threshold converges.
** The Kapur method
computes the threshold of an image by
log-transforming its values, then searching for the threshold that
maximizes the sum of entropies of the foreground and background
pixel values, when treated as separate distributions.
   You can also choose between Global, Adaptive, and Per object
thresholding:
Global: one threshold is used for the entire image (fast).
Adaptive: the threshold varies across the image - a bit slower but
provides more accurate edge determination which may help to separate
clumps, especially if you are not using a clump-separation method (see
below).
Per object: if you are using this module to find child objects located
*within* parent objects, the per object method will calculate a distinct
threshold for each parent object. This is especially helpful, for
example, when the background brightness varies substantially among the
parent objects. Important: the per object method requires that you run an
IdentifyPrim module to identify the parent objects upstream in the
pipeline. After the parent objects are identified in the pipeline, you
must then also run a Crop module as follows: the image to be cropped is the one
that you will want to use within this module to identify the children
objects (e.g., ChildrenStainedImage), and the shape in which to crop
is the name of the parent objects (e.g., Nuclei). Then, set this
IdentifyPrimAutomatic module to identify objects within the
CroppedChildrenStainedImage.

Threshold correction factor:
When the threshold is calculated automatically, it may consistently be
too stringent or too lenient. You may need to enter an adjustment factor
which you empirically determine is suitable for your images. The number 1
means no adjustment, 0 to 1 makes the threshold more lenient and greater
than 1 (e.g. 1.3) makes the threshold more stringent. For example, the
Otsu automatic thresholding inherently assumes that 50of the image is
covered by objects. If a larger percentage of the image is covered, the
Otsu method will give a slightly biased threshold that may have to be
corrected using a threshold correction factor.

Lower and upper bounds on threshold:
Can be used as a safety precaution when the threshold is calculated
automatically. For example, if there are no objects in the field of view,
the automatic threshold will be unreasonably low. In such cases, the
lower bound you enter here will override the automatic threshold.

Approximate percentage of image covered by objects:
An estimate of how much of the image is covered with objects. This
information is currently only used in the MoG (Mixture of Gaussian)
thresholding but may be used for other thresholding methods in the future
(see below).

Method to distinguish clumped objects:
Note: to choose between these methods, you can try test mode (see the
last setting for this module).
* Intensity - For objects that tend to have only one peak of brightness
per object (e.g. objects that are brighter towards their interiors), this
option counts each intensity peak as a separate object. The objects can
be any shape, so they need not be round and uniform in size as would be
required for a distance-based module. The module is more successful when
the objects have a smooth texture. By default, the image is automatically
blurred to attempt to achieve appropriate smoothness (see blur option),
but overriding the default value can improve the outcome on
lumpy-textured objects. Technical description: Object centers are defined
as local intensity maxima.
* Shape - For cases when there are definite indentations separating
objects. This works best for objects that are round. The intensity
patterns in the original image are irrelevant - the image is converted to
black and white (binary) and the shape is what determines whether clumped
objects will be distinguished. Therefore, the cells need not be brighter
towards the interior as is required for the Intensity option. The
de-clumping results of this method are affected by the thresholding
method you choose. Technical description: The binary thresholded image is
distance-transformed and object centers are defined as peaks in this
image. 

* None (fastest option) - If objects are far apart and are very well
separated, it may be unnecessary to attempt to separate clumped objects.
Using the 'None' option, a simple threshold will be used to identify
objects. This will override any declumping method chosen in the next
question.

Method to draw dividing lines between clumped objects:
* Intensity - works best where the dividing lines between clumped
objects are dim. Technical description: watershed on the intensity image.
* Distance - Dividing lines between clumped objects are based on the
shape of the clump. For example, when a clump contains two objects, the
dividing line will be placed where indentations occur between the two
nuclei. The intensity patterns in the original image are irrelevant - the
cells need not be dimmer along the lines between clumped objects.
Technical description: watershed on the distance-transformed thresholded
image.
* None (fastest option) - If objects are far apart and are very well
separated, it may be unnecessary to attempt to separate clumped objects.
Using the 'None' option, the thresholded image will be used to identify
objects. This will override any declumping method chosen in the above
question.

Size of smoothing filter, in pixel units:
   (Only used when distinguishing between clumped objects) This setting,
along with the suppress local maxima setting, affects whether objects
close to each other are considered a single object or multiple objects.
It does not affect the dividing lines between an object and the
background. If you see too many objects merged that ought to be separate,
the value should be lower. If you see too many objects split up that
ought to be merged, the value should be higher.
   The image is smoothed based on the specified minimum object diameter
that you have entered, but you may want to override the automatically
calculated value here. Reducing the texture of objects by increasing the
smoothing increases the chance that each real, distinct object has only
one peak of intensity but also increases the chance that two distinct
objects will be recognized as only one object. Note that increasing the
size of the smoothing filter increases the processing time exponentially.
%
Suppress local maxima within this distance (a positive integer, in pixel
units):
   (Only used when distinguishing between clumped objects) This setting,
along with the size of the smoothing filter, affects whether objects
close to each other are considered a single object or multiple objects.
It does not affect the dividing lines between an object and the
background. This setting looks for the maximum intensity in the size 
specified by the user.  The local intensity histogram is smoothed to 
remove the peaks within that distance. So,if you see too many objects 
merged that ought to be separate, the value should be lower. If you see 
too many objects split up that ought to be merged, the value should be higher.
   Object markers are suppressed based on the specified minimum object
diameter that you have entered, but you may want to override the
automatically calculated value here. The maxima suppression distance
should be set to be roughly equivalent to the minimum radius of a real
object of interest. Basically, any distinct 'objects' which are found but
are within two times this distance from each other will be assumed to be
actually two lumpy parts of the same object, and they will be merged.

Speed up by using lower-resolution image to find local maxima?
(Only used when distinguishing between clumped objects) If you have
entered a minimum object diameter of 10 or less, setting this option to
Yes will have no effect.

Technical notes: The initial step of identifying local maxima is
performed on the user-controlled heavily smoothed image, the
foreground/background is done on a hard-coded slightly smoothed image,
and the dividing lines between clumped objects (watershed) is done on the
non-smoothed image.

Laplacian of Gaussian method:
This is a specialized method to find objects and will override the above
settings in this module. The code was kindly donated by Zach Perlman and 
was used in this published work:
Multidimensional drug profiling by automated microscopy.
Science. 2004 Nov 12;306(5699):1194-8.  PMID: 15539606
Regrettably, we have no further description of its variables.

Special note on saving images: Using the settings in this module, object
outlines can be passed along to the module OverlayOutlines and then saved
with the SaveImages module. Objects themselves can be passed along to the
object processing module ConvertToImage and then saved with the
SaveImages module. This module produces several additional types of
objects with names that are automatically passed along with the following
naming structure: (1) The unedited segmented image, which includes
objects on the edge of the image and objects that are outside the size
range, can be saved using the name: UneditedSegmented + whatever you
called the objects (e.g. UneditedSegmentedNuclei). (2) The segmented
image which excludes objects smaller than your selected size range can be
saved using the name: SmallRemovedSegmented + whatever you called the
objects (e.g. SmallRemovedSegmented Nuclei).
"""
            
  
    def write_to_handles(self,handles):
        """Write out the module's state to the handles
        
        """
    
    def write_to_text(self,file):
        """Write the module's state, informally, to a text file
        """
        
    def run(self,pipeline,image_set,object_set,measurements, frame):
        """Run the module (abstract method)
        
        pipeline     - instance of CellProfiler.Pipeline for this run
        image_set    - the images in the image set being processed
        object_set   - the objects (labeled masks) in this image set
        measurements - the measurements for this run
        """
        #
        # Ignoring almost everything...
        #
        image = image_set.get_image(self.image_name.value)
        img = image.image
        mask = image.mask
        if len(img.shape)==3:
            # cheat - mini grayscale here
            img = numpy.sum(img,2)/img.shape[2]
        threshold = otsu(img,self.threshold_range.min,self.threshold_range.max)
        binary_image = numpy.logical_and((img >= threshold),mask)
        labeled_image,object_count = scipy.ndimage.label(binary_image)
        outline_image = labeled_image!=0
        temp = scipy.ndimage.binary_dilation(outline_image)
        outline_image = numpy.logical_and(temp,numpy.logical_not(outline_image))
        if frame:
            self.display(frame,image, labeled_image,outline_image)
        measurements.add_measurement('Image','Count_%s'%(self.object_name.value),numpy.array([object_count],dtype=float))
        measurements.add_measurement('Image','Threshold_FinalThreshold_%s'%(self.object_name.value),numpy.array([threshold],dtype=float))
        objects = cellprofiler.objects.Objects()
        objects.segmented = labeled_image
        object_set.add_objects(objects,self.object_name.value)
        #
        # Get the centers of each object - center_of_mass returns a list of two-tuples.
        #
        centers = scipy.ndimage.center_of_mass(numpy.ones(labeled_image.shape), labeled_image, range(1,object_count+1))
        centers = numpy.array(centers)
        centers = centers.reshape((object_count,2))
        location_center_x = centers[:,0]
        location_center_y = centers[:,1]
        measurements.add_measurement(self.object_name.value,'Location_Center_X', location_center_x)
        measurements.add_measurement(self.object_name.value,'Location_Center_Y', location_center_y)

    def display(self, frame, image, labeled_image, outline_image):
        """Display the image and labeling"""
        window_name = "CellProfiler(%s:%d)"%(self.module_name,self.module_num)
        my_frame=frame.FindWindowByName(window_name)
        if not my_frame:
            class my_frame_class(wx.Frame):
                def __init__(self):
                    wx.Frame.__init__(self,frame,-1,"Identify Primary Automatic",name=window_name)
                    sizer = wx.BoxSizer()
                    self.figure = figure= matplotlib.figure.Figure()
                    self.panel  = matplotlib.backends.backend_wxagg.FigureCanvasWxAgg(self,-1,self.figure) 
                    self.SetSizer(sizer)
                    sizer.Add(self.panel,1,wx.EXPAND)
                    self.Bind(wx.EVT_PAINT,self.on_paint)
                    self.orig_axes = self.figure.add_subplot(2,2,1)
                    self.outlined_axes = self.figure.add_subplot(2,2,3)
                    self.label_axes = self.figure.add_subplot(2,2,2)
                    self.Fit()
                    self.Show()
                def on_paint(self, event):
                    dc = wx.PaintDC(self)
                    self.panel.draw(dc)

            my_frame = my_frame_class()
            
        my_frame.orig_axes.clear()
        my_frame.orig_axes.imshow(image.image)
        my_frame.orig_axes.set_title("Original image")
        
        my_frame.label_axes.clear()
        my_frame.label_axes.imshow(labeled_image,matplotlib.cm.jet)
        my_frame.label_axes.set_title("Image labels")
        
        if image.image.ndim == 2:
            outline_img = numpy.ndarray(shape=(image.image.shape[0],image.image.shape[1],3))
            outline_img[:,:,0] = image.image 
            outline_img[:,:,1] = image.image 
            outline_img[:,:,2] = image.image
        else:
            outline_img = image.image.copy()
        outline_img[outline_image != 0,0]=1
        outline_img[outline_image != 0,1]=1 
        outline_img[outline_image != 0,2]=0 
        
        my_frame.outlined_axes.clear()
        my_frame.outlined_axes.imshow(outline_img)
        my_frame.outlined_axes.set_title("Outlined image")
        my_frame.Refresh()
         
    def get_categories(self,pipeline, object_name):
        """Return the categories of measurements that this module produces
        
        object_name - return measurements made on this object (or 'Image' for image measurements)
        """
        return ['Threshold','Location','NumberOfMergedObjects']
      
    def get_measurements(self, pipeline, object_name, category):
        """Return the measurements that this module produces
        
        object_name - return measurements made on this object (or 'Image' for image measurements)
        category - return measurements made in this category
        """
        return []
    
    def get_measurement_images(self,pipeline,object_name,category,measurement):
        """Return a list of image names used as a basis for a particular measure
        """
        return []
    
    def get_measurement_scales(self,pipeline,object_name,category,measurement,image_name):
        """Return a list of scales (eg for texture) at which a measurement was taken
        """
        return []
    
    def get_threshold_modifier(self):
        """The threshold algorithm modifier
        
        TM_GLOBAL                       = "Global"
        TM_ADAPTIVE                     = "Adaptive"
        TM_PER_OBJECT                   = "PerObject"
        """
        parts = self.threshold_method.value.split(' ')
        return parts[1]
    
    threshold_modifier = property(get_threshold_modifier)
    
    def get_threshold_algorithm(self):
        """The thresholding algorithm, for instance TM_OTSU"""
        parts = self.threshold_method.value.split(' ')
        return parts[0]
    
    threshold_algorithm = property(get_threshold_algorithm)