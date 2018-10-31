from __future__ import division, print_function, absolute_import

import numpy as np
from numpy.linalg import norm
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from .framework import Framework
from .configuration import Configuration
import time

class Circuit(object):
    """
    Set up a circuit
    Parameters:
    ----------
    sites: sequence of d floats
        Point coordinates in d dimension.
    bonds: tuple or array
        Edge list
    basis: array
        List of lattice vectors
    k: int/float or array of int/floats
        Spring constant
    varCell: array of booleans
        A list of lattice vector components
        allowed to change (1/True) or fixed (0/False).

    Returns
    -------
    The class does not return anything.
    """

    def __init__(self, sites, bonds, basis, k=1, varCell=None):

        self.N, self.dim = sites.shape
        self.nbasis = len(basis) # number of lattice vectors
        self.nchange = np.sum(varCell) # number of components allowed to change
        self.sites = sites
        self.bonds = bonds
        self.basis = basis
        self.varCell = varCell
        self.k = k
        self.center = np.mean(sites, axis=0) #center of mass
        PF = Framework(sites, bonds, basis, k, varCell)
        self.restlengths = PF.EdgeLengths()
        self.results = None

    def point(self, sites, bonds, basis):

        d = {'sites':None, 'lengths':None, 'direction':None,
             'eigenvalue':None, 'eigenvector':None}
        dim = self.dim
        N = self.N
        nchange = self.nchange

        '''create a framework, currently works only for 2D'''
        PF = Framework(sites, bonds, basis, self.k, self.varCell)
        evalues, evectors = PF.Eigenspace(eigvals=(0,dim+1))
        nzeros = np.sum(evalues < 1e-14) # number of zero eigenvalues
        if nzeros > dim + 1:
            print ('Warning: Rrigidity rank dropped!')

        # removing translations
        rhatSites = np.tile(np.eye(dim),N)
        rhatCell = np.zeros([dim,nchange],int)
        rhat = np.append(rhatSites,rhatCell,axis=1)/np.sqrt(N+nchange)
        e = evectors[0]
        projecions = np.multiply(e,rhat).sum(axis=1) # projection along each axis
        enet = e - np.dot(projecions,rhat)
        enet = enet / norm(enet)

        d['sites'] = sites
        d['lengths'] = PF.EdgeLengths()
        d['eigenvalue']= evalues[0]
        d['eigenvector']= evectors[0]
        d['direction'] = enet
        return d

    def nextPoint(self, sites, bonds, basis, direction, stepsize, threshold=0.99):

        #eigenvector for points and lattice vectors
        ## and change in lattice vectors
        eSites = direction[:-self.nchange].reshape(-1,self.dim)
        eCell = direction[-self.nchange:]
        latticeU = np.zeros_like(self.varCell,dtype=float)
        latticeU[self.varCell] = eCell
        eCell = latticeU.reshape(-1,self.dim)

        # initial step
        scale = stepsize
        nextP = sites + scale * eSites
        nextBasis = basis + scale * eCell
        nextPoint = self.point(nextP, bonds, basis)
        test = np.abs(np.vdot(direction,nextPoint['direction']))
        '''If dot product is less than threshold, decrease
        the step size until it is larger.'''
        while test < threshold:
            scale *= 0.5
            if scale < 10**(-10): break
            nextP = sites + scale * eSites
            nextBasis = basis + scale * eCell
            nextPoint = self.point(nextP, bonds, basis)
            test = np.abs(np.vdot(direction,nextPoint['direction']))
        return nextPoint, nextBasis

    def follow(self, stepsize=10**-3, iteration=10, radius=0.1,
                     relaxStep=5, report=True, optimization=False,
                     lazySearch=False, kick=1):
        '''Follow the circuit.'''
        d = {'sites':[], 'volume':[], 'distance':[],
             'basis':[], 'energy':[], 'nsteps': None,
             'stepsize': stepsize, 'time':None}

        p = np.copy(self.sites)
        bonds = self.bonds
        basis = self.basis
        restlengths = self.restlengths
        center = self.center
        dim = self.dim
        N = self.N


        timei = time.time()
        for i in range(iteration):

            # find direction for next step
            currentPoint = self.point(p, bonds, basis)
            translationVec = currentPoint['direction']
            lengths = currentPoint['lengths']
            eigval = currentPoint['eigenvalue']

            # make sure we move forward
            if i==0:
                translationVecOld = kick*translationVec
            projection = np.vdot(translationVec,translationVecOld)
            direction = np.sign(projection) * translationVec
            translationVecOld = direction

            # current volume, distance from center of mass, energy
            volume = np.abs(np.product(np.linalg.eig(basis)[0]))
            dist = np.mean(norm(p-center,axis=1))
            energy = 0.5*self.k*np.sum((lengths - restlengths)**2)

            # append current data
            d['sites'].append(p)
            d['volume'].append(volume)
            d['distance'].append(dist)
            d['basis'].append(basis)
            d['energy'].append(energy)

            # update
            nextP, nextBasis = self.nextPoint(p, bonds, basis, direction, stepsize)
            p = nextP['sites']
            basis = nextBasis

            if optimization and i!=0:
                if i%relaxStep==0:
                    C = rp.Configuration(p, bonds, basis, k, dim)
                    p = C.energy_minimize_Newton(L)
        d['nsteps'] = i+1
        timef=time.time()
        totalTime = timef-timei
        d['time'] = totalTime
        if report:
            print ('Total time={:<.4f} seconds'.format(totalTime))
        self.results = d
        return d

    def DotProduct(self,save=False,name=None):
        results = self.results
        nsteps = results['nsteps']
        results
        m,n = results['sites'][0].shape
        P = np.array(results['sites']).reshape(-1,m*n)
        T_diff = P[1:] - P[:-1]
        T_diff = T_diff/norm(T_diff,axis=1)[:,np.newaxis]

        delta = np.diag(np.dot(T_diff[1:,:],T_diff[:-1,:].T))
        mag = norm(P,axis=1)

        fig, (ax1,ax3) = plt.subplots(1,2,figsize=(12,6))
        ax1.plot(np.arange(1,nsteps-1),delta,'-r')
        ax1.set_xlabel('Iteration')
        # Make the y-axis label, ticks and tick labels match the line color.
        ax1.set_ylabel('Dot product', color='r')
        ax1.tick_params('y', colors='r')
        ax1.ticklabel_format(useOffset=False)
        #ax1.set_ylim(0.99,1)

        ax2 = ax1.twinx()
        ax2.plot(np.arange(nsteps),mag,'-ob',markersize=0.1)
        ax2.plot(np.arange(nsteps),np.ones(nsteps)*mag[0],'--k')
        ax2.set_ylabel('Distance from origin', color='b')
        ax2.tick_params('y', colors='b')
        ax2.ticklabel_format(useOffset=False)

        ax3.plot(np.arange(nsteps),results['volume'],'-ok',markersize=0.1)
        ax3.plot(np.arange(nsteps),np.ones(nsteps)*results['volume'][0],'--k')
        ax3.set_ylabel('Length of cut bond', color='k')
        ax3.set_xlabel('Iteration')

        ax4 = ax3.twinx()
        dists = norm(P-P[0],axis=1)
        ax4.plot(np.arange(nsteps),dists,'-og',markersize=0.1)
        ax4.set_ylabel('Distance from starting point', color='g')
        ax4.tick_params('y', colors='g')
        ax4.ticklabel_format(useOffset=False)

        fig.tight_layout()
        #now = datetime.datetime.now()
        #variables = map(str,[results['bond'],np.mean(lave),nsteps])
        #vars_strings = "_".join(variables)
        #name = 'trihex_lengths_'+vars_strings+'.pdf'
        #plt.title(name)
        plt.tight_layout()
        if save:
            plt.savefig(name,dpi=100)
            plt.close()
        else:
            plt.show(fig)