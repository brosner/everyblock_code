#include <Python.h>

int half_longest_match(PyObject* seq1, PyObject* seq2, int start1, int end1, int start2, int end2, int best_size, int* offset1, int* offset2) {
    int i, j, k, new_offset1, new_offset2;
    unsigned int current_size;

    for (i = start2, current_size = 0; i < end2; i++, current_size = 0) { // i is seq2 starting index.
        if (best_size >= end2 - i) break; // Short-circuit. See comment above.
        for (j = i, k = start1; k < end1 && j < end2; j++, k++) { // k is index of seq1, j is index of seq2.
            if (PyObject_RichCompareBool(PySequence_GetItem(seq1, k), PySequence_GetItem(seq2, j), Py_EQ)) {
                if (++current_size >= best_size) {
                    new_offset1 = k - current_size + 1;
                    new_offset2 = j - current_size + 1;
                    // Even if the current_size is the same as the best_size,
                    // it's a better fit if both offset1 and offset2 are lower.
                    // We want to be deterministic and make sure offset1 and
                    // offset2 are as close to the start of the list as possible.
                    if ((current_size > best_size) || (new_offset1 <= *offset1 && new_offset2 <= *offset2)) {
                        *offset1 = new_offset1;
                        *offset2 = new_offset2;
                    }
                    best_size = current_size;
                }
            }
            else {
                current_size = 0;
            }
        }
    }
    return best_size;
}

// offset1 and offset2 are relative to the *whole* string, not the substring
// (as defined by a_start and a_end).
// a_end and b_end are (the last index + 1).
int longest_common_subsequence(PyObject* seq1, PyObject* seq2, int start1, int end1, int start2, int end2, int* offset1, int* offset2) {
    unsigned int best_size;
    *offset1 = -1;
    *offset2 = -1;

    // If either sequence is empty, return 0.
    if (start1 == end1 || start2 == end2) {
        return 0;
    }

    best_size = half_longest_match(seq1, seq2, start1, end1, start2, end2, 0, offset1, offset2);
    best_size = half_longest_match(seq2, seq1, start2, end2, start1, end1, best_size, offset2, offset1);
    return best_size;
}

/* 
 PYTHON STUFF -- These are the hooks between Python and C.
*/

static PyObject * function_longest_common_subsequence(PyObject *self, PyObject *args) {
    PyObject* seq1;
    PyObject* seq2;
    int offset1, offset2;
    unsigned int best_size;

    if (!PyArg_ParseTuple(args, "OO", &seq1, &seq2))
        return NULL;

    if (!PySequence_Check(seq1) || !PySequence_Check(seq2)) {
        PyErr_SetString(PyExc_TypeError, "This function's arguments must be sequences");
        return NULL;
    }

    Py_INCREF(seq1);
    Py_INCREF(seq2);
    best_size = longest_common_subsequence(seq1, seq2, 0, PySequence_Length(seq1), 0, PySequence_Length(seq2), &offset1, &offset2);
    Py_DECREF(seq1);
    Py_DECREF(seq2);

    return Py_BuildValue("(iii)", best_size, offset1, offset2);
}

static PyMethodDef ModuleMethods[] = {
    {"longest_common_subsequence", function_longest_common_subsequence, METH_VARARGS, ""},
    {NULL, NULL, 0, NULL}        // sentinel
};

PyMODINIT_FUNC initlistdiffc(void) {
    (void) Py_InitModule("listdiffc", ModuleMethods);
}
