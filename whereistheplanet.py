import os
import argparse
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import h5py
from astropy.time import Time

import orbitize.kepler as kepler

basedir = os.path.dirname(__file__)
datadir = os.path.join(basedir, "data")

def print_prediction(date_mjd, chains, tau_ref_epoch, num_samples=None):
    """
    Prints out a prediction for the prediction of a planet given a set of posterior draws

    Args:
        date_mjd (float): MJD of date for which we want a prediction
        chains (np.array): Nx8 array of N orbital elements. Orbital elements are ordered as:
                            sma, ecc, inc, aop, pan, tau, plx, mtot
        tau_ref_epoch (float): MJD for reference epoch of tau (see orbitize for details on tau)
        num_samples (int): number of random samples for prediction. If None, will use all of them

    Returns:
        ra_args (tuple): a two-element tuple of the median RA offset, and stddev of RA offset
        dec_args (tuple): a two-element tuple of the median Dec offset, and stddev of Dec offset
        sep_args (tuple): a two-element tuple of the median separation offset, and stddev of sep offset
        PA args (tuple): a two-element tuple of the median PA offset, and stddev of PA offset
    """

    if num_samples is None:
        num_samples = chains.shape[0]
        rand_draws = np.arange(num_samples) # don't need to randomize
    else:
        if num_samples > chains.shape[0]:
            print("Requested too many samples. Maximum is {0}.".format(chains.shape[0]))
            return
    
        # randomly draw values
        rand_draws = np.random.randint(0, chains.shape[0], num_samples)

    rand_orbits = chains[rand_draws]

    sma = rand_orbits[:, 0]
    ecc = rand_orbits[:, 1]
    inc = rand_orbits[:, 2]
    aop = rand_orbits[:, 3]
    pan = rand_orbits[:, 4]
    tau = rand_orbits[:, 5]
    plx = rand_orbits[:, 6]
    mtot = rand_orbits[:, 7]

    rand_ras, rand_decs, rand_vzs = kepler.calc_orbit(date_mjd, sma, ecc, inc, aop, pan, tau, plx, mtot,
                                                     tau_ref_epoch=tau_ref_epoch)

    rand_seps = np.sqrt(rand_ras**2 + rand_decs**2)
    rand_pas = np.degrees(np.arctan2(rand_ras, rand_decs)) % 360

    ra_args = np.median(rand_ras), np.std(rand_ras)
    dec_args = np.median(rand_decs), np.std(rand_decs)
    sep_args = np.median(rand_seps), np.std(rand_seps)
    pa_args = np.median(rand_pas), np.std(rand_pas)

    print("RA Offset = {0:.3f} +/- {1:.3f} mas".format(ra_args[0], ra_args[1]))
    print("Dec Offset = {0:.3f} +/- {1:.3f} mas".format(dec_args[0], dec_args[1]))
    print("Separation = {0:.3f} +/- {1:.3f} mas".format(sep_args[0], sep_args[1]))
    print("PA = {0:.3f} +/- {1:.3f} deg".format(pa_args[0], pa_args[1]))

    return ra_args, dec_args, sep_args, pa_args




post_dict = {'hr8799b' : "post_hr8799b.hdf5",
             'hr8799c' : "post_hr8799c.hdf5",
             'hr8799d' : "post_hr8799d.hdf5",
             'hr8799e' : "post_hr8799e.hdf5",
             'betapicb' : "post_betapicb.hdf5",
             'betpicb' : "post_betapicb.hdf5", #also accept betpicb for beta pic b
             'hd206893b' : "post_hd206893b.hdf5"}

def print_supported_orbits():
    """
    Prints out to the screen currently supported orbits
    """
    # list all possible planet options
    # right now all possible orbits are in the keys to post_dict
    for name in post_dict:
        print("    " + name)
    return

def get_chains(planet_name):
    """
    Return posteriors for a given planet name

    Args:
        planet_name (str): name of planet. no space

    Returns:
        chains (np.array): Nx8 array of N posterior draws
        tau_ref_epoch (float): MJD for reference tau epoch
    """
    planet_name = planet_name.lower()

    # handle any exceptions as necessary here
    if planet_name == "betpicb":
        planet_name = "betapicb"

    if planet_name not in post_dict:
        raise ValueError("Invalid planet name '{0}'".format(planet_name))
    
    filename = post_dict[planet_name]
    filepath = os.path.join(datadir, filename)
    with h5py.File(filepath,'r') as hf: # Opens file for reading
        post = np.array(hf.get('post'))
        tau_ref_epoch = float(hf.attrs['tau_ref_epoch'])
    
    return post, tau_ref_epoch



########## Main Function ##########
if __name__ == "__main__":
    # parse input arguments
    parser = argparse.ArgumentParser(description='Predicts the location of a companion based on the current knowledge of its orbit')
    parser.add_argument("planet_name", help="Name of the planet. No spaces", default="",  nargs='?')
    parser.add_argument("-t", "--time", help="UT Time to evaluate at. Either MJD or YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")
    parser.add_argument('-l', '--list', action='store_true', help='Lists all the possible orbits currently supported')
    args = parser.parse_args()

    if args.list:
        print("Current supported orbits:")
        print_supported_orbits()
    elif args.planet_name == "":
        print("No planet name passed in. Here are the currently supported ones:")
        print_supported_orbits()

    else:
        # perform regular functionality.
        if args.time is None:
            # use the current time
            time_mjd = Time.now().mjd
        else:
            # check if it is MJD. Otherwise astropy.time can read it and give MJD
            if "-" in args.time:
                # dashes mean not MJD. Probably formatted as a date
                time_mjd = Time(args.time).mjd
            else:
                time_mjd = float(args.time)

        # do real stuff
        chains, tau_ref_epoch = get_chains(args.planet_name)

        print_prediction(time_mjd, chains, tau_ref_epoch, num_samples=100)

