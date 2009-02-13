"""measureobjectintensity - take intensity measurements on an object set

"""
__version__="$Revision$"

import numpy as np
import scipy.ndimage as nd

import cellprofiler.cpmodule as cpm
import cellprofiler.settings as cps
import cellprofiler.cpmath.outline as cpmo

INTENSITY = 'Intensity'
INTEGRATED_INTENSITY = 'IntegratedIntensity'
MEAN_INTENSITY = 'MeanIntensity'
STD_INTENSITY = 'StdIntensity'
MIN_INTENSITY = 'MinIntensity'
MAX_INTENSITY = 'MaxIntensity'
INTEGRATED_INTENSITY_EDGE = 'IntegratedIntensityEdge'
MEAN_INTENSITY_EDGE = 'MeanIntensityEdge'
STD_INTENSITY_EDGE = 'StdIntensityEdge'
MIN_INTENSITY_EDGE = 'MinIntensityEdge'
MAX_INTENSITY_EDGE = 'MaxIntensityEdge'
MASS_DISPLACEMENT = 'MassDisplacement'
LOWER_QUARTILE_INTENSITY = 'LowerQuartileIntensity'
MEDIAN_INTENSITY = 'MedianIntensity'
UPPER_QUARTILE_INTENSITY = 'UpperQuartileIntensity'

ALL_MEASUREMENTS = [INTEGRATED_INTENSITY, MEAN_INTENSITY, STD_INTENSITY,
                        MIN_INTENSITY, MAX_INTENSITY, INTEGRATED_INTENSITY_EDGE,
                        MEAN_INTENSITY_EDGE, STD_INTENSITY_EDGE,
                        MIN_INTENSITY_EDGE, MAX_INTENSITY_EDGE, 
                        MASS_DISPLACEMENT, LOWER_QUARTILE_INTENSITY,
                        MEDIAN_INTENSITY, UPPER_QUARTILE_INTENSITY]

class MeasureObjectIntensity(cpm.CPModule):
    """% SHORT DESCRIPTION:
Measures several intensity features for identified objects.
*************************************************************************

Given an image with objects identified (e.g. nuclei or cells), this
module extracts intensity features for each object based on a
corresponding grayscale image. Measurements are recorded for each object.

Features measured:       Feature Number:
IntegratedIntensity     |       1
MeanIntensity           |       2
StdIntensity            |       3
MinIntensity            |       4
MaxIntensity            |       5
IntegratedIntensityEdge |       6
MeanIntensityEdge       |       7
StdIntensityEdge        |       8
MinIntensityEdge        |       9
MaxIntensityEdge        |      10
MassDisplacement        |      11
LowerQuartileIntensity  |      12
MedianIntensity         |      13
UpperQuartileIntensity  |      14

How it works:
Retrieves objects in label matrix format and a corresponding original
grayscale image and makes measurements of the objects. The label matrix
image should be "compacted": that is, each number should correspond to an
object, with no numbers skipped. So, if some objects were discarded from
the label matrix image, the image should be converted to binary and
re-made into a label matrix image before feeding it to this module.

Intensity Measurement descriptions:

* IntegratedIntensity - The sum of the pixel intensities within an
 object.
* MeanIntensity - The average pixel intensity within an object.
* StdIntensity - The standard deviation of the pixel intensities within
 an object.
* MaxIntensity - The maximal pixel intensity within an object.
* MinIntensity - The minimal pixel intensity within an object.
* IntegratedIntensityEdge - The sum of the edge pixel intensities of an
 object.
* MeanIntensityEdge - The average edge pixel intensity of an object.
* StdIntensityEdge - The standard deviation of the edge pixel intensities
 of an object.
* MaxIntensityEdge - The maximal edge pixel intensity of an object.
* MinIntensityEdge - The minimal edge pixel intensity of an object.
* MassDisplacement - The distance between the centers of gravity in the
 gray-level representation of the object and the binary representation of
 the object.
* LowerQuartileIntensity - the intensity value of the pixel for which 25%
 of the pixels in the object have lower values.
* MedianIntensity - the median intensity value within the object
* UpperQuartileIntensity - the intensity value of the pixel for which 75%
 of the pixels in the object have lower values.

For publication purposes, it is important to note that the units of
intensity from microscopy images are usually described as "Intensity
units" or "Arbitrary intensity units" since microscopes are not 
callibrated to an absolute scale. Also, it is important to note whether 
you are reporting either the mean or the integrated intensity, so specify
"Mean intensity units" or "Integrated intensity units" accordingly.

See also MeasureImageIntensity.
"""
    variable_revision_number = 2
    category = "Measurement"
    
    def create_settings(self):
        self.module_name = "MeasureObjectIntensity"
        self.image_name = cps.ImageNameSubscriber("What did you call the grayscale images you want to process?","None")
        self.object_names = [cps.ObjectNameSubscriber("What did you call the objects that you want to measure?","None")]
        self.object_name_remove_buttons = [cps.DoSomething("Remove this object","Remove",self.remove_cb,0)]
        self.object_name_add_button = cps.DoSomething("Add another object","Add",self.add_cb)
    
    def remove_cb(self, index):
        del self.object_names[index]
        del self.object_name_remove_buttons[index]
    
    def add_cb(self):
        nitems = len(self.object_names)
        self.object_names.append(cps.ObjectNameSubscriber("What did you call the objects that you want to measure?","None"))
        self.object_name_remove_buttons.append(cps.DoSomething("Remove this object","Remove",self.remove_cb,nitems))

    def visible_settings(self):
        result = [self.image_name]
        for object_name,remove_button in zip(self.object_names, 
                                             self.object_name_remove_buttons):
            result.extend((object_name,remove_button))
        result.append(self.object_name_add_button)
        return result
    
    def settings(self):
        result = [self.image_name]
        result.extend(self.object_names)
        return result

    def set_setting_values(self,setting_values,variable_revision_number,module_name):
        """Adjust the number of object_names according to the number of
        setting values, then call the superclass to set the object names
        to the variable values
        """
        if variable_revision_number ==1:
            raise NotImplementedError("Can't read version # 1")
        if module_name != self.module_class():
            # Old matlab-style. Erase any setting values that are
            # "Do not use"
            new_setting_values = [setting_values[0]]
            for setting_value in setting_values[1:]:
                if setting_value != cps.DO_NOT_USE:
                    new_setting_values.append(setting_value)
            setting_values = new_setting_values
            modue_name = self.module_class()
        object_count = len(setting_values)-1
        while len(self.object_names) > object_count:
            self.remove_cb(len(self.object_names)-1)
        while len(self.object_names) < object_count:
            self.add_cb()
        super(MeasureObjectIntensity,self).set_setting_values(setting_values, 
                                                              variable_revision_number, 
                                                              module_name)

    def get_categories(self,pipeline, object_name):
        """Get the categories of measurements supplied for the given object name
        
        pipeline - pipeline being run
        object_name - name of labels in question (or 'Images')
        returns a list of category names
        """
        for object_name_variable in self.object_names:
            if object_name_variable == object_name:
                return [INTENSITY]
        return []
    
    def get_measurements(self, pipeline, object_name, category):
        """Get the measurements made on the given object in the given category"""
        if category != INTENSITY:
            return []
        for object_name_variable in self.object_names:
            if object_name_variable == object_name:
                return ALL_MEASUREMENTS
    
    def get_measurement_images(self, pipeline,object_name, category, measurement):
        """Get the images used to make the given measurement in the given category on the given object"""
        if category != INTENSITY:
            return []
        if measurement not in ALL_MEASUREMENTS:
            return []
        for object_name_variable in self.object_names:
            if object_name_variable == object_name:
                return [self.image_name.value]
        return []
    
    def run(self, workspace):
        image = workspace.image_set.get_image(self.image_name.value,
                                              must_be_grayscale=True)
        image = image.pixel_data
        for object_name in self.object_names:
            objects = workspace.object_set.get_objects(object_name.value)
            labels   = objects.segmented
            nobjects = np.max(labels)+1
            outlines = cpmo.outline(labels)
            
            integrated_intensity = np.array(nd.sum(image,labels,
                                                   range(nobjects)))
            integrated_intensity_edge = np.array(nd.sum(image,outlines,
                                                        range(nobjects)))
            mean_intensity = np.array(nd.mean(image,labels,
                                              range(nobjects)))
            mean_intensity_edge = np.array(nd.mean(image,outlines,
                                                   range(nobjects)))
            std_intensity = np.array(nd.standard_deviation(image, labels, 
                                                           range(nobjects)))
            std_intensity_edge = np.array(nd.standard_deviation(image, outlines, 
                                                                range(nobjects)))
            min_intensity = np.array(nd.minimum(image, labels, range(nobjects)))
            min_intensity_edge = np.array(nd.minimum(image,outlines,
                                                     range(nobjects)))
            max_intensity = np.array(nd.maximum(image,labels,range(nobjects)))
            max_intensity_edge = np.array(nd.maximum(image,outlines,
                                                     range(nobjects)))
            # The mass displacement is the distance between the center
            # of mass of the binary image and of the intensity image. The
            # center of mass is the average X or Y for the binary image
            # and the sum of X or Y * intensity / integrated intensity
            if nobjects > 1:
                mesh_x, mesh_y = np.meshgrid(range(image.shape[1]),
                                             range(image.shape[0]))
                cm_x = np.array(nd.mean(mesh_x,labels,range(nobjects)))
                cm_y = np.array(nd.mean(mesh_y,labels,range(nobjects)))
                
                i_x = np.array(nd.sum(mesh_x * image,labels,range(nobjects)))
                i_y = np.array(nd.sum(mesh_y * image,labels,range(nobjects)))
                cmi_x = i_x / integrated_intensity
                cmi_y = i_y / integrated_intensity
                diff_x = cm_x - cmi_x
                diff_y = cm_y - cmi_y
                mass_displacement = np.sqrt(diff_x * diff_x+diff_y*diff_y)[1:]
            else:
                mass_displacement = np.zeros((0,))
            
            # We do the quantile measurements using an indexing trick:
            # given a label integer L and the intensity at that label, I
            # L+I is a number between L and L+1. So if you add the label
            # matrix to the intensity matrix and sort, you'll get the
            # intensities in order by label, then by magnitude. If you
            # do a cumsum of areas of labels, you'll get indices into
            # the ordered array and you can read out quantiles pretty easily
            
            if nobjects > 1:
                areas = np.array(nd.sum(np.ones(labels.shape,int), labels,
                                        range(nobjects)))
                indices = np.cumsum(areas)[:-1]
                ordered_image = image + labels.astype(float)
                ordered_image = ordered_image.flatten()
                ordered_image.sort()
                indices_25 = (indices+areas[1:]/4+.5).astype(int)
                indices_50 = (indices+areas[1:]/2+.5).astype(int)
                indices_75 = (indices+3*areas[1:] / 4 +.5).astype(int)
                lower_quartile_intensity = (ordered_image[indices_25] - 
                                            range(1,nobjects))
                median_intensity         = (ordered_image[indices_50] - 
                                            range(1,nobjects))
                upper_quartile_intensity = (ordered_image[indices_75] - 
                                            range(1,nobjects))
            else:
                lower_quartile_intensity = np.zeros((0,))
                median_intensity = np.zeros((0,))
                upper_quartile_intensity = np.zeros((0,))
            
            if nobjects > 1:
                integrated_intensity = integrated_intensity[1:]
                mean_intensity = mean_intensity[1:]
                std_intensity = std_intensity[1:]
                min_intensity = min_intensity[1:]
                max_intensity = max_intensity[1:]

                integrated_intensity_edge = integrated_intensity_edge[1:]
                mean_intensity_edge = mean_intensity_edge[1:]
                std_intensity_edge = std_intensity_edge[1:]
                min_intensity_edge = min_intensity_edge[1:]
                max_intensity_edge = max_intensity_edge[1:]
            else:
                integrated_intensity = np.zeros((0,))
                mean_intensity = np.zeros((0,))
                std_intensity = np.zeros((0,))
                min_intensity = np.zeros((0,))
                max_intensity = np.zeros((0,))

                integrated_intensity_edge = np.zeros((0,))
                mean_intensity_edge = np.zeros((0,))
                std_intensity_edge = np.zeros((0,))
                min_intensity_edge = np.zeros((0,))
                max_intensity_edge = np.zeros((0,))
                
            
            m = workspace.measurements
            for feature_name, measurement in \
                ((INTEGRATED_INTENSITY, integrated_intensity),
                 (MEAN_INTENSITY, mean_intensity),
                 (STD_INTENSITY, std_intensity),
                 (MIN_INTENSITY, min_intensity),
                 (MAX_INTENSITY, max_intensity),
                 (INTEGRATED_INTENSITY_EDGE, integrated_intensity_edge),
                 (MEAN_INTENSITY_EDGE, mean_intensity_edge),
                 (STD_INTENSITY_EDGE, std_intensity_edge),
                 (MIN_INTENSITY_EDGE, min_intensity_edge),
                 (MAX_INTENSITY_EDGE, max_intensity_edge),
                 (MASS_DISPLACEMENT, mass_displacement),
                 (LOWER_QUARTILE_INTENSITY, lower_quartile_intensity),
                 (MEDIAN_INTENSITY, median_intensity),
                 (UPPER_QUARTILE_INTENSITY, upper_quartile_intensity)):
                measurement_name = "%s_%s_%s"%(INTENSITY,feature_name,
                                               self.image_name.value)
                m.add_measurement(object_name.value,measurement_name, 
                                  measurement)