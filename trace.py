#!/usr/bin/env python
# -*- coding: utf-8 -*-

from subprocess import PIPE, run
import time
import numpy as np
import argparse
import os
from configparser import ConfigParser

def parse_args():
    return _build_parser().parse_args()


def _build_parser():
    parser = argparse.ArgumentParser()
    _add_common_arguments(parser)
    return parser


def _add_common_arguments(parser):
    parser.add_argument("config", help="config file for trace.py simulation")
    parser.add_argument(
        "-c",
        action="store",
        type=int,
        default=os.cpu_count() if os.cpu_count() is not None else 1,
        help="number of cores (default: '%(default)s')",
    )
    parser.add_argument(
        "-img",
        action="store_true",
        default=False,
        help="generates luminances maps",
    )
    parser.add_argument(
        "-date", 
        nargs="+", 
        help="simulates a specific date in mmddhh format"
    )
    parser.add_argument(
        "-ab", help="ambient bounces (default: '%(default)s')", type=int, default=3
    )
    parser.add_argument(
        "-ad", help="ambient divisions (default: '%(default)s')", type=int, default=500
    )
    parser.add_argument(
        "-direct", 
        action="store_true",
        default=False,
        help="calculates glare even if the solar disk is not in the field of view", 
    )

class Config:
    pass


def parse_config(config_path, options):
    parser = ConfigParser()
    parser.read(config_path)
    config = Config()
    _add_variables(parser, config)  
    _add_paths(parser, config) 
    _add_inputs(parser, config) 
    return config

def _add_variables(parser, config):
    config.lat = parser.getfloat("VARIABLES", "lat")
    config.lon = parser.getfloat("VARIABLES", "lon")
    config.mer = parser.getfloat("VARIABLES", "mer")

def _add_paths(parser, config):    
    config.inDir = parser.get("PATHS", "inDir")
    config.workDir = parser.get("PATHS", "workDir")
    config.outDir = parser.get("PATHS", "outDir")

def _add_inputs(parser, config):    
    config.matFile = parser.get("PATHS", "matFile")
    config.roomFile = parser.get("PATHS", "roomFile")
    config.glazFile = parser.get("PATHS", "glazFile")
    config.shadFile = parser.get("PATHS", "shadFile")  
    config.viewPoint = parser.get("PATHS", "viewPoint")
    config.obstacles=parser.get("PATHS", "obstacles")

def shell(cmd, outputFlag=False):
    print(cmd)
    stdout = PIPE if outputFlag else None
    completedProcess = run(cmd, stdout=stdout, stderr=PIPE, shell=True, check=True)
    if outputFlag:
        return completedProcess.stdout.decode("utf-8")

def gen_view_file(pts, workDir):
    for i in range(len(pts)):
        with open("%sview_%i.vf" % (workDir,i), "w") as fw:
            tx, ty, tz = pts[i, 0], pts[i, 1], pts[i, 2]
            rx, ry, rz = pts[i, 3], pts[i, 4], pts[i, 5]
            fw.write(
                "rview -vta -vp %1.3f %1.3f %1.3f -vd %1.3f %1.3f %1.3f -vv 180 -vh 180 -vs 0 -vl 0 -vu 0 0 1\n"
                % (tx, ty, tz, rx, ry, rz)
            )
        with open("%ssensor_%i.pts" % (workDir,i), "w") as fw:
            tx, ty, tz = pts[i, 0], pts[i, 1], pts[i, 2]
            rx, ry, rz = pts[i, 3], pts[i, 4], pts[i, 5]
            fw.write(
                "%1.3f %1.3f %1.3f %1.3f %1.3f %1.3f\n"
                % (tx, ty, tz, rx, ry, rz)
            )

def calculate_dgp(fileDGP,month,day,hour,lat,lon,mer,workDir,inDir,matFile,roomFile,obstacles,shadFile,glazFile,ab,ad,aa,aS,lw,n,pts,runFlag=0):
    # daylight hours
    skySTR =" gensky %d %d %.2f +s -a %.2f -o %.2f -m %.1f" % (month,day,hour,lat,lon,mer)
    coordsun = shell(skySTR,True)
    sunAltitude = float(coordsun.split()[22])
    if sunAltitude > 0: 
        print('daylight hour',sunAltitude)
        skyt="sky.rad"    
        skySTR =" gensky %d %d %.2f +s -a %.2f -o %.2f -m %.1f > %s%s " % (month,day,hour,lat,lon,mer,workDir,skyt)
        octSTR=" oconv %s%s %s%s %s%s %s%s %s%s %s%s %s%s > %sscene.oct"%(workDir,skyt,inDir,matFile,inDir,roomFile,inDir,obstacles,inDir,shadFile,inDir,glazFile,workDir,SKfile,workDir)  
        shell(skySTR)
        shell(octSTR)
        # Visible solar disk hours
        mainSTR="rtrace -h -I -ab 0 -ad %d -aa %.2f -as %d -lw %.8f -n %d -ov %sscene.oct <%ssensor_%i.pts"%(ad,aa,aS,lw,n,workDir,workDir,pts)
        result = shell(mainSTR,True)
        illuDirect = float(result.split()[0])*179
        if illuDirect > 0.1 or runFlag: 
            print('visible solar disk hour',illuDirect)        
            # Point-in-time illuminance calculation:
            mainSTR="rtrace -h -I -ab %d -ad %d -aa %.2f -as %d -lw %.8f -n %d -ov %sscene.oct <%ssensor_%i.pts"%(ab,ad,aa,aS,lw,n,workDir,workDir,pts)
            result = shell(mainSTR,True)
            illuVert = float(result.split()[0])*179
            # Point-in-time image calculation:
            if opts.img:
                mainSTR=" vwrays -ff -x %d -y %d -vf %sview_%i.vf | rtrace  -n %d -ab %d -ad %d -aa %.2f -as %d -lw %.8f -st %.8f -ld -ov -ffc $(vwrays -d -x %d -y %d -vf %sview_%i.vf) -h+ %sscene.oct > %s%i%i%i_%i.hdr"%(Nx,Ny,workDir,pts,n,ab,ad,aa,aS,lw,st,Nx,Ny,workDir,pts,workDir,outDir,month,day,hour,pts)
                shell(mainSTR)
                falSTR="falsecolor -ip %s%i%i%i_%i.hdr -l cd/m2 -lw 75 -s 5000 -n 5 | ra_tiff -z - %s%i%i%i_%i.tif"%(outDir,month,day,hour,pts,outDir,month,day,hour,pts)
                shell(falSTR)
                evalSTR = "evalglare -vta -vh 180 -vv 180 -vu 0 0 1 %s%i%i%i_%i.hdr"%(outDir,month,day,hour,pts)
                result = shell(evalSTR,True)
                dgp = float(result.split()[1])
            else:
                mainSTR="vwrays -ff -x %d -y %d -vf %sview_%i.vf | rtrace  -n %d -ab %d -ad %d -aa %.2f -as %d -lw %.8f -st %.8f -ld -ov -ffc $(vwrays -d -x %d -y %d -vf %sview_%i.vf) -h+ %sscene.oct | evalglare -vta -vh 180 -vv 180 -vu 0 0 1" %(Nx,Ny,workDir,pts,n,ab,ad,aa,aS,lw,st,Nx,Ny,workDir,pts,workDir)
                result = shell(mainSTR,True)
                dgp = float(result.split()[1])
            print('DGP',dgp,'illuVert',illuVert)
            fileDGP.write("%d %d %1.1f %.3f %i \n"%(int(month),int(day),hour,dgp,illuVert))

def annual_eval(outDir,pts):
    dgpValue = np.genfromtxt("%sdgp_%i.out"%(outDir,pts), delimiter=" ",usecols=3)
    fDGPe35 = 0
    fDGPe40 = 0
    fDGPe45 = 0
    for i in range(len(dgpValue)):
        if dgpValue[i] > 0.35:
           fDGPe35 = fDGPe35 +1
        if dgpValue[i] > 0.40:
           fDGPe40 = fDGPe40 +1
        if dgpValue[i] > 0.45:
           fDGPe45 = fDGPe45 +1
    fDGPe35 = fDGPe35*5.43/1304
    fDGPe40 = fDGPe40*5.43/1304
    fDGPe45 = fDGPe45*5.43/1304
    fDGPe = [fDGPe35,fDGPe40,fDGPe45]
    np.savetxt("%sfDGPe_%i.out"%(outDir,pts), fDGPe,delimiter=" ",fmt="%1.3f")


if __name__ == "__main__":
    if 1==1:
        opts = parse_args()
        config_path =opts.config
        config = parse_config(config_path, opts)
        #_add_variables    
        inDir=config.inDir
        workDir=config.workDir
        outDir=config.outDir
        #_add_inputs   
        aa=0.1
        lw=0.002
        st=0.15
        aS=1000
        Ny=900 
        Nx=900
        Npts=9
        SKfile="skyglowM.rad"
        # ---
        projectWorkDir = workDir.split("/")[0]+"/"+workDir.split("/")[1]
        projectOutDir = outDir.split("/")[0]+"/"+outDir.split("/")[1]
        if not os.path.exists(projectWorkDir):
            shell("mkdir %s"%(projectWorkDir))
        if not os.path.exists(projectOutDir):
            shell("mkdir %s"%(projectOutDir))
        if not os.path.exists(workDir):
            shell("mkdir %s"%(workDir))
        if not os.path.exists(outDir):
            shell("mkdir %s"%(outDir))
            cad="skyfunc glow groundglow 0 0 4 1 1 1 0 \ngroundglow source ground 0 0 4 0 0 -1 180 \nskyfunc glow skyglow 0 0 4 1 1 1 0 \nskyglow source skydome 0 0 4 0 0 1 180"      
            fileSK=open("%s%s"%(workDir,SKfile),"w")
            fileSK.write("%s"%(cad)); fileSK.close()
        # --
        fileTime=open("%stime.out"%outDir,"w")
        inobis = [4,4,4,4,4,3]
        t1=time.time()
        # generate view file
        illuPts = np.atleast_2d(np.genfromtxt('%s%s'%(inDir,config.viewPoint), delimiter=" "))
        gen_view_file(illuPts, workDir)
        for pts in range(len(illuPts)):
            # output file
            fileDGP=open("%sdgp_%i.out"%(outDir,pts),"w")
            # dynamic simulation
            if opts.date:
                for i in range(len(opts.date)):
                    month = int(opts.date[i][:2])
                    day = int(opts.date[i][2:4])
                    hour = float(opts.date[i][4:])+0.5
                    print(month,day,hour)
                    calculate_dgp(fileDGP,month,day,hour,config.lat,config.lon,config.mer,workDir,inDir,config.matFile,\
                        config.roomFile,config.obstacles,config.shadFile,config.glazFile,opts.ab,opts.ad,\
                        aa,aS,lw,opts.c,pts,1)
            else:
                for i in range(6):
                    month = i+1
                    for j in range(inobis[i]):
                        day = j*7+1
                        for k in range(24):
                            hour = k+0.5
                            print(month,day,hour)
                            calculate_dgp(fileDGP,month,day,hour,config.lat,config.lon,config.mer,workDir,inDir,config.matFile,\
                                config.roomFile,config.obstacles,config.shadFile,config.glazFile,opts.ab,opts.ad,\
                                aa,aS,lw,opts.c,pts,opts.direct)
                month = 12
                day = 22
                for k in range(24):
                    hour = k+0.5
                    print(month,day,hour)
                    calculate_dgp(fileDGP,month,day,hour,config.lat,config.lon,config.mer,workDir,inDir,config.matFile,\
                        config.roomFile,config.obstacles,config.shadFile,config.glazFile,opts.ab,opts.ad,\
                        aa,aS,lw,opts.c,pts,opts.direct)
            fileDGP.close() 
        t2=time.time()
        fileTime.write("%d %.3f \n"%(opts.c,abs(t2-t1),))
        print("CPU time: %.1f s "%(abs(t2-t1)))
        fileTime.close()
        if not opts.date:
            for pts in range(len(illuPts)):
                annual_eval(outDir,pts)
