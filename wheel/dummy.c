/* https://docs.python.org/3/extending/extending.html#a-simple-example */
#define PY_SSIZE_T_CLEAN
#include <Python.h>#include <Python.h>

static PyObject *
spam_system(PyObject *self, PyObject *args)
{
    const char *command;
    int sts;

    if (!PyArg_ParseTuple(args, "s", &command))
        return NULL;
    sts = system(command);
    return PyLong_FromLong(sts);
}

PyMODINIT_FUNC
PyInit_dummy(void)
{
    return PyModuleDef_Init(&spam_system);
}
