#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 10 11:59:30 2019

@author: slacour
"""

import os
filedir = os.path.dirname(os.path.realpath(__file__)) # gets the directory the current python script is in
parent_dir = os.path.dirname(filedir) # up one leve
module_dir = os.path.join(parent_dir, "whereistheplanet")
import sys
sys.path.insert(0, module_dir) # add parent dir to python path
import whereistheplanet

import json
import numpy as np
import subprocess

def get_xy(planet_name,timeOfObs):
    if planet_name == "HD206893b":
        return 124,200
    values=whereistheplanet.predict_planet(planet_name,timeOfObs)
    return values[0][0],values[1][0]

def makeSequence(seq,obs,timeOfObs):

    # retreive observing block main parameters
    runID=obs["runID"]
    star=obs["star"]
    RA=obs["RA"]
    DEC=obs["DEC"]
    pmRA=obs["pmRA"]
    pmDEC=obs["pmDEC"]
    Kmag=obs["Kmag"]
    Hmag=obs["Hmag"]
    GSmag=obs["GSmag"]
    resolution=obs["resolution"]
    wollaston=obs["wollaston"]


    # check observing sequence, looking for error or inconsistency.
    planet1=seq["planets"][0]
    Nplanet=len(seq["planets"])
    if 'swap' not in seq:
        seq['swap'] = False
    if (Nplanet!=len(seq["dit planets"])|(Nplanet!=len(seq["ndit planets"]))) :
        raise ValueError("The sequence has a wrong number of planets/dit/ndits")
    if ((seq['axis']!="on")&(seq['axis']!="off")):
        raise ValueError("The sequence has wrong axis value (must be on or off)")
    if ((seq['swap']!=True)&(Nplanet!=1)):
        raise ValueError("A swap can only be done with a single companion (here %i)"%Nplanet)



    # axis off or on

    # do test sur la sequence


    Sequence_templates={
            "template1" :{
                    "type": "header",
                    "run ID": runID,
                    "OB name": star,
                    "Obs time": timeOfObs,
                    },
            "template2" :{
                    "type": "acquisition",
                    "target name": planet1,
                    "RA": RA,
                    "DEC": DEC,
                    "pmRA": pmRA,
                    "pmDEC": pmDEC,
                    "K mag": Kmag,
                    "H mag": Hmag,
                    "resolution": resolution,
                    "wollaston": wollaston,
                    "GS mag": GSmag
                    }
            }

    RA_init,DEC_init=get_xy(planet1,timeOfObs)
    if (seq["axis"]=="on")&(seq["swap"]!=True):
            ratio=1/100
            mOffset=max([RA_init,DEC_init])
            if mOffset > 999:
                off=mOffset-999
                ratio=max([1/100,off/mOffset])
            else:
                ratio=1/100
            RA_init*=ratio
            DEC_init*=ratio
    Sequence_templates["template2"]["RA offset"]=RA_init
    Sequence_templates["template2"]["DEC offset"]=DEC_init
    if seq['swap']==True:
        swap_repeat=2
    else:
        swap_repeat=1

    if seq["axis"] == "on":
        for s in range(swap_repeat):
            for r in range(obs["repeat"]):
                new_template = {
                    "type": "observation",
                    "name science": star,
                    "RA offset":-RA_init,
                    "DEC offset":-DEC_init,
                    "DIT": seq["dit star"],
                    "NDIT": seq["ndit star"],
                    "sequence":"O",
                    }
                if (s==2):
                    RA_planet,DEC_planet=get_xy(planet1,timeOfObs)
                    new_template["RA_planet"]=-RA_planet+RA_init
                    new_template["DEC_planet"]=-DEC_planet+DEC_init
                if seq["repeat"]>1:
                    if (len(Sequence_templates)==3+2*((seq["repeat"]-1)//2)): 
                        new_template["sequence"]="O S"
                Sequence_templates["template%i"%(len(Sequence_templates)+1)]=new_template

                for name,dit,ndit in zip(seq["planets"],seq["dit planets"],seq["ndit planets"]):
                    RA_planet,DEC_planet=get_xy(name,timeOfObs)
                    if (s==2):
                        RA_planet,DEC_planet=-RA_planet,-DEC_planet
                    new_template = {
                        "type": "observation",
                        "name science": name,
                        "RA offset":RA_planet-RA_init,
                        "DEC offset":DEC_planet-DEC_init,
                        "DIT": dit,
                        "NDIT": ndit,
                        "sequence":"O",
                        }
                    if (s==2):
                        new_template["RA_planet"]=RA_init
                        new_template["DEC_planet"]=DEC_init

                    Sequence_templates["template%i"%(len(Sequence_templates)+1)]=new_template
            
            if (s==1)&(seq['swap']==True):
                new_template = {
                    "type": "swap"
                }
                Sequence_templates["template%i"%(len(Sequence_templates)+1)]=new_template
    
        if seq['swap']!=True:
            new_template = {
                "type": "observation",
                "name science": star,
                "RA offset":-RA_init,
                "DEC offset":-DEC_init,
                "DIT": obs["dit star"],
                "NDIT": obs["ndit star"],
                "sequence":"O",
                }
            Sequence_templates["template%i"%(len(Sequence_templates)+1)]=new_template


        if obs["axis"] == "off":
            for s in range(swap_repeat):
                for r in range(obs["repeat"]):
                    for n in range(Nplanet):
                        name,dit,ndit=obs["planets"],obs["dit planets"],obs["ndit planets"]
                        if n > 1:
                            RA_init,DEC_init=get_xy(name,timeOfObs)
                            new_template = {
                                "type": "dither",
                                "name science": name,
                                "mag science": Kmag+9,
                                "RA offset":RA_init,
                                "DEC offset":DEC_init,
                                }
                            Sequence_templates["template%i"%(len(Sequence_templates)+1)]=new_template
                        new_template = {
                            "type": "observation",
                            "name science": name,
                            "RA offset":0.0,
                            "DEC offset":0.0,
                            "DIT": dit,
                            "NDIT": ndit,
                            "sequence":"O",
                            }
                        Sequence_templates["template%i"%(len(Sequence_templates)+1)]=new_template
                if (s==1)&(seq['swap']==True):
                    new_template = {
                        "type": "swap"
                    }
                    Sequence_templates["template%i"%(len(Sequence_templates)+1)]=new_template


    Total_time=0.0
    for n in range(len(Sequence_templates)):
        s=Sequence_templates["template%i"%(n+1)]
        if s["type"]=="acquisition":
            Total_time+=10
        if s["type"]=="dither":
            Total_time+=1
        if s["type"]=="observation":
            Total_time+=s["DIT"]*s["NDIT"]/60*1.1*len(s['sequence'].replace(' ',''))

    print("Estimated time for OB: %i hours, %i min"%(int(Total_time/60),int(Total_time%60)))

    with open("OBs/"+star+".json", 'w') as f:
        json.dump(Sequence_templates, f)

    return Sequence_templates

def send_to_wgv(star,computer):
    p=subprocess.Popen(["scp","OBs/"+star+".obd",computer+':targets/exoplanets/.'])
    sts=os.waitpid(p.pid,0)
