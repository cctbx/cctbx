#define PY_SSIZE_T_CLEAN // Required for Py_ssize_t
#include <Python.h>

// C function to be exposed to Python
static PyObject* my_module_add(PyObject* self, PyObject* args) {
    int a, b;

    // Parse Python arguments: "ii" expects two integers
    if (!PyArg_ParseTuple(args, "ii", &a, &b)) {
        return NULL; // Return NULL on error, Python will raise an exception
    }

    // Perform the addition and return the result as a Python integer
    return Py_BuildValue("i", a + b);
}

// Method definition table
static PyMethodDef MyModuleMethods[] = {
    {"add", my_module_add, METH_VARARGS, "Adds two integers."},
    {NULL, NULL, 0, NULL} // Sentinel to mark the end of the array
};

// Module definition structure
static struct PyModuleDef my_module = {
    PyModuleDef_HEAD_INIT,
    "my_module", // Name of the module in Python
    "A simple example module.", // Module docstring
    -1, // Size of per-interpreter state of the module, or -1 if the module keeps state in global variables.
    MyModuleMethods
};

// Module initialization function
PyMODINIT_FUNC PyInit_my_module(void) {
    return PyModule_Create(&my_module);
}
