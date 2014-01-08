#!/usr/bin/env python
# encoding: utf-8
"""
utilities.py

Created by Andrew Ning on 2013-05-31.
Copyright (c) NREL. All rights reserved.
"""

import numpy as np
from scipy.linalg import solve_banded


def cosd(value):
    """cosine of value where value is given in degrees"""

    return np.cos(np.radians(value))


def sind(value):
    """sine of value where value is given in degrees"""

    return np.sin(np.radians(value))


def tand(value):
    """tangent of value where value is given in degrees"""

    return np.tan(np.radians(value))


def hstack(vec):
    """stack arrays horizontally.  useful for assemblying Jacobian
    assumes arrays are column vectors (if rows just use concatenate)"""
    newvec = []
    for v in vec:
        if len(v.shape) == 1:
            newvec.append(v[:, np.newaxis])
        else:
            newvec.append(v)

    return np.hstack(newvec)


def vstack(vec):
    """stack arrays vertically
    assumes arrays are row vectors.  if columns use concatenate"""

    newvec = []
    for v in vec:
        if len(v.shape) == 1:
            newvec.append(v[np.newaxis, :])
        else:
            newvec.append(v)

    return np.vstack(newvec)


def _checkIfFloat(x):
    try:
        n = len(x)
    except TypeError:  # if x is just a float
        x = np.array([x])
        n = 1

    return x, n


def linspace_with_deriv(start, stop, num):

    step = (stop-start)/float((num-1))
    y = np.arange(0, num) * step + start
    y[-1] = stop

    # gradients
    const = np.arange(0, num) * 1.0/float((num-1))
    dy_dstart = -const + 1.0
    dy_dstart[-1] = 0.0

    dy_dstop = const
    dy_dstop[-1] = 1.0

    return y, dy_dstart, dy_dstop


def interp_with_deriv(x, xp, yp):
    # TODO: put in Fortran to speed up

    x, n = _checkIfFloat(x)

    if np.any(np.diff(xp) < 0):
        raise TypeError('xp must be in ascending order')

    # n = len(x)
    m = len(xp)

    y = np.zeros(n)
    dydx = np.zeros(n)
    dydxp = np.zeros((n, m))
    dydyp = np.zeros((n, m))

    for i in range(n):
        if x[i] < xp[0]:
            j = 0  # linearly extrapolate
        elif x[i] > xp[-1]:
            j = m-2
        else:
            for j in range(m-1):
                if xp[j+1] > x[i]:
                    break
        x1 = xp[j]
        y1 = yp[j]
        x2 = xp[j+1]
        y2 = yp[j+1]

        y[i] = y1 + (y2 - y1)*(x[i] - x1)/(x2 - x1)
        dydx[i] = (y2 - y1)/(x2 - x1)
        dydxp[i, j] = (y2 - y1)*(x[i] - x2)/(x2 - x1)**2
        dydxp[i, j+1] = -(y2 - y1)*(x[i] - x1)/(x2 - x1)**2
        dydyp[i, j] = 1 - (x[i] - x1)/(x2 - x1)
        dydyp[i, j+1] = (x[i] - x1)/(x2 - x1)

    if n == 1:
        y = y[0]

    return y, np.diag(dydx), dydxp, dydyp


def cubic_with_deriv(x, xp, yp):

    x, n = _checkIfFloat(x)

    if np.any(np.diff(xp) < 0):
        raise TypeError('xp must be in ascending order')

    # n = len(x)
    m = len(xp)

    y = np.zeros(n)
    dydx = np.zeros(n)
    dydxp = np.zeros((n, m))
    dydyp = np.zeros((n, m))

    xk = xp[1:-1]
    yk = yp[1:-1]
    xkp = xp[2:]
    ykp = yp[2:]
    xkm = xp[:-2]
    ykm = yp[:-2]

    b = (ykp - yk)/(xkp - xk) - (yk - ykm)/(xk - xkm)
    l = (xk - xkm)/6.0
    d = (xkp - xkm)/3.0
    u = (xkp - xk)/6.0
    # u[0] = 0.0  # non-existent entries
    # l[-1] = 0.0

    # solve for second derivatives
    fpp = solve_banded((1, 1), np.matrix([u, d, l]), b)
    fpp = np.concatenate([[0.0], fpp, [0.0]])  # natural spline

    # find location in vector
    for i in range(n):
        if x[i] < xp[0]:
            j = 0
        elif x[i] > xp[-1]:
            j = m-2
        else:
            for j in range(m-1):
                if xp[j+1] > x[i]:
                    break
        x1 = xp[j]
        y1 = yp[j]
        x2 = xp[j+1]
        y2 = yp[j+1]

        A = (x2 - x[i])/(x2 - x1)
        B = 1 - A
        C = 1.0/6*(A**3 - A)*(x2 - x1)**2
        D = 1.0/6*(B**3 - B)*(x2 - x1)**2

        y[i] = A*y1 + B*y2 + C*fpp[j] + D*fpp[j+1]
        dAdx = -1.0/(x2 - x1)
        dBdx = -dAdx
        dCdx = 1.0/6*(3*A**2 - 1)*dAdx*(x2 - x1)**2
        dDdx = 1.0/6*(3*B**2 - 1)*dBdx*(x2 - x1)**2
        dydx[i] = dAdx*y1 + dBdx*y2 + dCdx*fpp[j] + dDdx*fpp[j+1]

    if n == 1:
        y = y[0]
        dydx = dydx[0]

    return y


def _smooth_maxmin(yd, ymax, maxmin, pct_offset=0.01, dyd=None):

    yd, n = _checkIfFloat(yd)

    y1 = (1-pct_offset)*ymax
    y2 = (1+pct_offset)*ymax

    if maxmin == 'min':
        f1 = y1
        f2 = ymax
        g1 = 1.0
        g2 = 0.0
        idx_constant = yd >= y2

    elif maxmin == 'max':
        f1 = ymax
        f2 = y2
        g1 = 0.0
        g2 = 1.0
        idx_constant = yd <= y1

    f = CubicSplineSegment(y1, y2, f1, f2, g1, g2)

    # main region
    ya = np.copy(yd)
    if dyd is None:
        dya_dyd = np.ones_like(yd)
    else:
        dya_dyd = np.copy(dyd)

    # cubic spline region
    idx = np.logical_and(yd > y1, yd < y2)
    ya[idx] = f.eval(yd[idx])
    dya_dyd[idx] = f.eval_deriv(yd[idx])

    # constant region
    ya[idx_constant] = ymax
    dya_dyd[idx_constant] = 0.0

    if n == 1:
        ya = ya[0]
        dya_dyd = dya_dyd[0]


    return ya, dya_dyd


def smooth_max(yd, ymax, pct_offset=0.01, dyd=None):
    return _smooth_maxmin(yd, ymax, 'max', pct_offset, dyd)


def smooth_min(yd, ymin, pct_offset=0.01, dyd=None):
    return _smooth_maxmin(yd, ymin, 'min', pct_offset, dyd)



def smooth_abs(x, dx=0.01):

    x, n = _checkIfFloat(x)

    y = np.abs(x)
    idx = np.logical_and(x > -dx, x < dx)
    y[idx] = x[idx]**2/(2.0*dx) + dx/2.0

    # gradient
    dydx = np.ones_like(x)
    dydx[x <= -dx] = -1.0
    dydx[idx] = x[idx]/dx


    if n == 1:
        y = y[0]
        dydx = dydx[0]

    return y, dydx



class CubicSplineSegment(object):

    def __init__(self, x1, x2, f1, f2, g1, g2):

        self.x1 = x1
        self.x2 = x2

        self.A = np.array([[x1**3, x1**2, x1, 1.0],
                  [x2**3, x2**2, x2, 1.0],
                  [3*x1**2, 2*x1, 1.0, 0.0],
                  [3*x2**2, 2*x2, 1.0, 0.0]])
        self.b = np.array([f1, f2, g1, g2])

        self.coeff = np.linalg.solve(self.A, self.b)

        self.poly = np.polynomial.Polynomial(self.coeff[::-1])


    def eval(self, x):
        return self.poly(x)


    def eval_deriv(self, x):
        polyd = self.poly.deriv()
        return polyd(x)


    def eval_deriv_params(self, xvec, dx1, dx2, df1, df2, dg1, dg2):

        x1 = self.x1
        x2 = self.x2
        dA_dx1 = np.matrix([[3*x1**2, 2*x1, 1.0, 0.0],
                  [0.0, 0.0, 0.0, 0.0],
                  [6*x1, 2.0, 0.0, 0.0],
                  [0.0, 0.0, 0.0, 0.0]])
        dA_dx2 = np.matrix([[0.0, 0.0, 0.0, 0.0],
                  [3*x2**2, 2*x2, 1.0, 0.0],
                  [0.0, 0.0, 0.0, 0.0],
                  [6*x2, 2.0, 0.0, 0.0]])
        df = np.array([df1, df2, dg1, dg2])
        c = np.matrix(self.coeff).T

        n = len(xvec)
        dF = np.zeros(n)
        for i in range(n):
            x = np.array([xvec[i]**3, xvec[i]**2, xvec[i], 1.0])
            d = np.linalg.solve(self.A.T, x)
            dF_dx1 = -d*dA_dx1*c
            dF_dx2 = -d*dA_dx2*c
            dF_df = np.linalg.solve(self.A.T, x)
            dF[i] = np.dot(dF_df, df) + dF_dx1[0]*dx1 + dF_dx2[0]*dx2

        return dF



def _getvar(comp, name):
    vars = name.split('.')
    base = comp
    for var in vars:
        base = getattr(base, var)

    return base


def _setvar(comp, name, value):
    vars = name.split('.')
    base = comp
    for i in range(len(vars)-1):
        base = getattr(base, vars[i])

    setattr(base, vars[-1], value)


def check_gradient_unit_test(unittest, comp, fd='central', step_size=1e-6, tol=1e-6, display=False):

    names, errors = check_gradient(comp, fd, step_size, tol, display)

    for name, err in zip(names, errors):
        try:
            unittest.assertLessEqual(err, tol)
        except AssertionError, e:
            print '*** error in:', name
            raise e


def check_gradient(comp, fd='central', step_size=1e-6, tol=1e-6, display=False):

    comp.run()
    comp.linearize()
    inputs, outputs, J = comp.provideJ()

    # compute size of Jacobian
    m = 0
    mvec = []  # size of each output
    cmvec = []  # cumulative size of outputs
    nvec = []  # size of each input
    cnvec = []  # cumulative size of inputs
    for out in outputs:
        f = _getvar(comp, out)
        if np.array(f).shape == ():
            msub = 1
        else:
            msub = len(f)
        m += msub
        mvec.append(msub)
        cmvec.append(m)
    n = 0
    for inp in inputs:
        x = _getvar(comp, inp)
        if np.array(x).shape == ():
            nsub = 1
        else:
            nsub = len(x)
        n += nsub
        nvec.append(nsub)
        cnvec.append(n)

    JFD = np.zeros((m, n))

    if J.shape != JFD.shape:
        raise TypeError('Incorrect Jacobian size. Your provided Jacobian is of shape {}, but it should be ({}, {})'.format(J.shape, m, n))


    # initialize start and end indices of where to insert into Jacobian
    m1 = 0
    m2 = 0


    for i, out in enumerate(outputs):

        # get function value at center
        f = _getvar(comp, out)
        if np.array(f).shape == ():
            lenf = 1
        else:
            f = np.copy(f)  # so not pointed to same memory address
            lenf = len(f)

        m2 += lenf

        n1 = 0

        for j, inp in enumerate(inputs):

            # get x value at center (save location)
            x = _getvar(comp, inp)
            if np.array(x).shape == ():
                x0 = x
                lenx = 1
            else:
                x = np.copy(x)  # so not pointing to same memory address
                x0 = np.copy(x)
                lenx = len(x)

            for k in range(lenx):

                # take a step
                if lenx == 1:
                    h = step_size*x
                    if h == 0:
                        h = step_size
                    x += h
                else:
                    h = step_size*x[k]
                    if h == 0:
                        h = step_size
                    x[k] += h
                _setvar(comp, inp, x)
                comp.run()

                # fd
                fp = np.copy(_getvar(comp, out))

                if fd == 'central':

                    # step back
                    if lenx == 1:
                        x -= 2*h
                    else:
                        x[k] -= 2*h
                    _setvar(comp, inp, x)
                    comp.run()

                    fm = np.copy(_getvar(comp, out))

                    deriv = (fp - fm)/(2*h)

                else:
                    deriv = (fp - f)/h


                JFD[m1:m2, n1+k] = deriv

                # reset state
                x = np.copy(x0)
                _setvar(comp, inp, x0)
                comp.run()

            n1 += lenx

        m1 = m2

    # error checking
    namevec = []
    errorvec = []

    if display:
        print '{:<20} ({}) {:<10} ({}, {})'.format('error', 'errortype', 'name', 'analytic', 'fd')
        print

    for i in range(m):
        for j in range(n):

            # get corresonding variables names
            for ii in range(len(mvec)):
                if cmvec[ii] > i:
                    oname = 'd_' + outputs[ii]

                    if mvec[ii] > 1:  # need to print indices
                        subtract = 0
                        if ii > 0:
                            subtract = cmvec[ii-1]
                        idx = i - subtract
                        oname += '[' + str(idx) + ']'

                    break
            for jj in range(len(nvec)):
                if cnvec[jj] > j:
                    iname = 'd_' + inputs[jj]

                    if nvec[jj] > 1:  # need to print indices
                        subtract = 0
                        if jj > 0:
                            subtract = cnvec[jj-1]
                        idx = j - subtract
                        iname += '[' + str(idx) + ']'

                    break
            name = oname + ' / ' + iname

            # compute error
            if np.abs(J[i, j]) <= tol:
                errortype = 'absolute'
                error = J[i, j] - JFD[i, j]
            else:
                errortype = 'relative'
                error = 1.0 - JFD[i, j]/J[i, j]
            error = np.abs(error)

            # display
            if error > tol:
                star = ' ***** '
            else:
                star = ''

            if display:
                output = '{}{:<20} ({}) {}: ({}, {})'.format(star, error, errortype, name, J[i, j], JFD[i, j])
                print output

            # save
            namevec.append(name)
            errorvec.append(error)

    return namevec, errorvec



# if __name__ == '__main__':



    # xpt = np.array([1.0, 2.0, 4.0, 6.0, 10.0, 12.0])
    # ypt = np.array([5.0, 12.0, 14.0, 16.0, 21.0, 29.0])

    # # interpolate  (extrapolation will work, but beware the results may be silly)
    # n = 50
    # x = np.linspace(0.0, 13.0, n)
    # y = cubic_with_deriv(x, xpt, ypt)

    # import matplotlib.pyplot as plt
    # plt.plot(xpt, ypt, 'o')
    # plt.plot(x, y, '-')
    # plt.show()
