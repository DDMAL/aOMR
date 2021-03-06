


#include "gameramodule.hpp"
#include "knnmodule.hpp"

#include "aruspix_plugin.hpp"

#include <string>
#include <stdexcept>
#include "Python.h"
#include <list>

using namespace Gamera;


extern "C" {
#ifndef _MSC_VER
    void init_aruspix_plugin(void);
#endif
    static PyObject* call_extract(PyObject* self, PyObject* args);
    static PyObject* call_visualize(PyObject* self, PyObject* args);
    static PyObject* call_flatten(PyObject* self, PyObject* args);
}

static PyMethodDef _aruspix_plugin_methods[] = {
{ CHAR_PTR_CAST "extract",
call_extract, METH_VARARGS,
CHAR_PTR_CAST "**extract** (``Choice`` [music staves|borders|ornate letters|in staff text|lyrics|titles] *Category* = music staves)\n\nExtract on plan of the image. The music staves (black in the pre-classified\nimage in Aruspix), the border (light grey), ornate letters (dark green), the text\nin staff (light green), the lyrics (orange) and the titles (yellow). The image return\nis a black and white one with the selected content"        },
{ CHAR_PTR_CAST "visualize",
call_visualize, METH_VARARGS,
CHAR_PTR_CAST "**visualize** ()\n\nVisualize the pre-classified image of the Aruspix file. The different categories\nare shown in the corresponding colours, with black for the music staves, light grey for \nthe borders, dark green for the ornate letters, and so on...\n"        },
{ CHAR_PTR_CAST "flatten",
call_flatten, METH_VARARGS,
CHAR_PTR_CAST "**flatten** ()\n\nFlatten the image content into a black and white image. Everything\nwhich is not white in the original image is considered as black\n"        },
{ NULL }
};

static PyObject* call_extract(PyObject* self, PyObject* args) {
    
    PyErr_Clear();
    Image* return_arg;
    PyObject* return_pyarg;
    Image* self_arg;
    PyObject* self_pyarg;
    int Category_arg;
    
    if (PyArg_ParseTuple(args, CHAR_PTR_CAST "Oi:extract"
                         ,
                         &self_pyarg                        ,
                         &Category_arg                      ) <= 0)
        return 0;
    
    if (!is_ImageObject(self_pyarg)) {
        PyErr_SetString(PyExc_TypeError, "Argument 'self' must be an image");
        return 0;
    }
    self_arg = ((Image*)((RectObject*)self_pyarg)->m_x);
    image_get_fv(self_pyarg, &self_arg->features, &self_arg->features_len);
    
    try {
        switch(get_image_combination(self_pyarg)) {
            case GREYSCALEIMAGEVIEW:
                return_arg = extract(*((GreyScaleImageView*)self_arg), Category_arg);
                break;
            default:
                PyErr_Format(PyExc_TypeError,"The 'self' argument of 'extract' can not have pixel type '%s'. Acceptable value is GREYSCALE.", get_pixel_type_name(self_pyarg));
                return 0;
        }
    } catch (std::exception& e) {
        PyErr_SetString(PyExc_RuntimeError, e.what());
        return 0;
    }
    
    if (return_arg== NULL) {
        if (PyErr_Occurred() == NULL) {
            Py_INCREF(Py_None);
            return Py_None;
        } else
            return NULL;
    } else {
        return_pyarg = create_ImageObject(return_arg);              return return_pyarg;
    }
}
static PyObject* call_visualize(PyObject* self, PyObject* args) {
    
    PyErr_Clear();
    Image* return_arg;
    PyObject* return_pyarg;
    Image* self_arg;
    PyObject* self_pyarg;
    
    if (PyArg_ParseTuple(args, CHAR_PTR_CAST "O:visualize"
                         ,
                         &self_pyarg                      ) <= 0)
        return 0;
    
    if (!is_ImageObject(self_pyarg)) {
        PyErr_SetString(PyExc_TypeError, "Argument 'self' must be an image");
        return 0;
    }
    self_arg = ((Image*)((RectObject*)self_pyarg)->m_x);
    image_get_fv(self_pyarg, &self_arg->features, &self_arg->features_len);
    
    try {
        switch(get_image_combination(self_pyarg)) {
            case GREYSCALEIMAGEVIEW:
                return_arg = visualize(*((GreyScaleImageView*)self_arg));
                break;
            default:
                PyErr_Format(PyExc_TypeError,"The 'self' argument of 'visualize' can not have pixel type '%s'. Acceptable value is GREYSCALE.", get_pixel_type_name(self_pyarg));
                return 0;
        }
    } catch (std::exception& e) {
        PyErr_SetString(PyExc_RuntimeError, e.what());
        return 0;
    }
    
    if (return_arg== NULL) {
        if (PyErr_Occurred() == NULL) {
            Py_INCREF(Py_None);
            return Py_None;
        } else
            return NULL;
    } else {
        return_pyarg = create_ImageObject(return_arg);              return return_pyarg;
    }
}
static PyObject* call_flatten(PyObject* self, PyObject* args) {
    
    PyErr_Clear();
    Image* return_arg;
    PyObject* return_pyarg;
    Image* self_arg;
    PyObject* self_pyarg;
    
    if (PyArg_ParseTuple(args, CHAR_PTR_CAST "O:flatten"
                         ,
                         &self_pyarg                      ) <= 0)
        return 0;
    
    if (!is_ImageObject(self_pyarg)) {
        PyErr_SetString(PyExc_TypeError, "Argument 'self' must be an image");
        return 0;
    }
    self_arg = ((Image*)((RectObject*)self_pyarg)->m_x);
    image_get_fv(self_pyarg, &self_arg->features, &self_arg->features_len);
    
    try {
        switch(get_image_combination(self_pyarg)) {
            case GREYSCALEIMAGEVIEW:
                return_arg = flatten(*((GreyScaleImageView*)self_arg));
                break;
            default:
                PyErr_Format(PyExc_TypeError,"The 'self' argument of 'flatten' can not have pixel type '%s'. Acceptable value is GREYSCALE.", get_pixel_type_name(self_pyarg));
                return 0;
        }
    } catch (std::exception& e) {
        PyErr_SetString(PyExc_RuntimeError, e.what());
        return 0;
    }
    
    if (return_arg== NULL) {
        if (PyErr_Occurred() == NULL) {
            Py_INCREF(Py_None);
            return Py_None;
        } else
            return NULL;
    } else {
        return_pyarg = create_ImageObject(return_arg);              return return_pyarg;
    }
}

DL_EXPORT(void) init_aruspix_plugin(void) {
    Py_InitModule(CHAR_PTR_CAST "_aruspix_plugin", _aruspix_plugin_methods);
}


