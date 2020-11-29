"""Calculates the vertical illuminance and DGP at view points.

For each view point defined in the 'viewPoint' file, the program calculates luminance maps of the field of view by raytracing (Radiance program rtrace), which are then passed to evalgare to calculate the Daylight Glare Probability (DGP). If the option -img is selected, the program also generates a falsecolor picture of the field of view. If a datum is provided (option -date), the calculation is done for the given instant assuming a clear sky. More than one datum can be provided. Without the option -date, the program runs for one day per week during half a year, calculating every hour in which the solar disk is in the field of view. The program runs gensky to determine if the solar altitude is positive as a condition for a daylighting hour. For a daylighing hour, runs rtrace -ab 0 to determine if the solar disk is in the field of view as a condition to run rtrace with ab > 0 (option -ab, default ab = 3). If the option -direct is selected, the calculation is done for the daylighting hours of one day per week. The option -c selects the number of cores for a multicore Radiance calculation.

  Typical usage example:

  python3 ./glare/trace.py {directory_path}/config.ini -c 5 -ab 4
  python3 ./glare/trace.py {directory_path}/config.ini -c 5 -img -date 110510

"""

from subprocess import PIPE, run
import time
import numpy as np
import argparse
import os
from configparser import ConfigParser


"""Parse arguments"""


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
        "-date", nargs="+", help="simulates specific dates in mmddhh format"
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


"""Parse configuration"""


def parse_config(config_path):
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
    config.obstacles = parser.get("PATHS", "obstacles")


def _create_non_existing_directories(config):
    if hasattr(config, "outDir") and not os.path.exists(config.outDir):
        os.makedirs(config.outDir)
    if hasattr(config, "workDir") and not os.path.exists(config.workDir):
        os.makedirs(config.workDir)
    if not os.path.isfile("%sskyglowM.rad" % workDir):
        cad = "skyfunc glow groundglow 0 0 4 1 1 1 0 \ngroundglow source ground 0 0 4 0 0 -1 180 \nskyfunc glow skyglow 0 0 4 1 1 1 0 \nskyglow source skydome 0 0 4 0 0 1 180"
        fileSK = open("%sskyglowM.rad" % workDir, "w")
        fileSK.write("%s" % (cad))
        fileSK.close()


""" run shell commands """


def shell(cmd, output_flag=False):
    print(cmd)
    stdout = PIPE if output_flag else None
    _completed_process = run(
        cmd, stdout=stdout, stderr=PIPE, shell=True, check=True)
    if output_flag:
        return _completed_process.stdout.decode("utf-8")


""" generate view and sensor files from viewPoints """


def gen_view_file(view_points, workDir):
    for i in range(len(view_points)):
        with open("%sview_%i.vf" % (workDir, i), "w") as fw:
            tx, ty, tz = view_points[i,
                                     0], view_points[i, 1], view_points[i, 2]
            rx, ry, rz = view_points[i,
                                     3], view_points[i, 4], view_points[i, 5]
            fw.write(
                "rview -vta -vp %1.3f %1.3f %1.3f -vd %1.3f %1.3f %1.3f -vv 180 -vh 180 -vs 0 -vl 0 -vu 0 0 1\n"
                % (tx, ty, tz, rx, ry, rz)
            )
        with open("%ssensor_%i.pts" % (workDir, i), "w") as fw:
            tx, ty, tz = view_points[i,
                                     0], view_points[i, 1], view_points[i, 2]
            rx, ry, rz = view_points[i,
                                     3], view_points[i, 4], view_points[i, 5]
            fw.write("%1.3f %1.3f %1.3f %1.3f %1.3f %1.3f\n" %
                     (tx, ty, tz, rx, ry, rz))


def calculate_dgp(
    output_file,
    month,
    day,
    hour,
    config,
    opts,
    radiance_param,
    pts,
    flag_direct=0,
):
    # daylight hours
    _sky_str = f"gensky {month} {day} {hour} +s -a {config.lat} -o {config.lon} -m {config.mer}"
    _coordsun = shell(_sky_str, True)
    sun_altitude = float(_coordsun.split()[22])
    if sun_altitude > 0:
        np.savetxt(f"{config.workDir}sky.rad", _sky_str)
        # Radiance octree
        _oct_str = f"oconv {config.workDir}sky.rad {config.matFile} {config.roomFile} {config.obstacles} {config.shadFile} {config.glazFile} {config.workDir}skyglowM.rad > {config.workDir}scene.oct"
        shell(_oct_str)
        # Visible solar disk hours
        _rtrace_str = f"rtrace -h -I -ab 0 -ad {opts.ad} -aa {radiance_param.aa} -as {radiance_param.aS} -lw {radiance_param.lw} -n {opts.c} -ov {config.workDir}scene.oct <{config.workDir}sensor_{pts}.pts"
        _rtrace_result = shell(_rtrace_str, True)
        _illuminance_direct = float(_rtrace_result.split()[0]) * 179
        if _illuminance_direct > 0.1 or flag_direct:
            # Point-in-time illuminance calculation
            _rtrace_str = f"rtrace -h -I -ab {opts.ab} -ad {opts.ad} -aa {radiance_param.aa} -as {radiance_param.aS} -lw {radiance_param.lw} -n {opts.c} -ov {config.workDir}scene.oct <{config.workDir}sensor_{pts}.pts"
            _rtrace_result = shell(_rtrace_str, True)
            illuminance = float(_rtrace_result.split()[0]) * 179
            # Point-in-time image calculation
            if opts.img:
                _vwrays_str = f"vwrays -ff -x {radiance_param.x_dimension} -y {radiance_param.y_dimension} -vf {config.workDir}view_{pts}.vf | rtrace  -n {opts.c} -ab {opts.ab} -ad {opts.ad} -aa {radiance_param.aa} -as {radiance_param_aS} -lw {radiance_param.lw} -st {radiance_param.st} -ld -ov -ffc $(vwrays -d -x {radiance_param.x_dimension} -y {radiance_param.y_dimension} -vf {config.workDir}view_{pts}.vf) -h+ {workDir}scene.oct > {config.outDir}{month}{day}{hour}_{pts}.hdr"
                shell(_vwrays_str)
                _falsecolor_str = f"falsecolor -ip {config.outDir}{month}{day}{hour}_{pts}.hdr -l cd/m2 -lw 75 -s 5000 -n 5 | ra_tiff -z - {config.outDir}{month}{day}{hour}_{pts}.tif"
                shell(_falsecolor_str)
                _evalglare_str = f"evalglare -vta -vh 180 -vv 180 -vu 0 0 1 {config.outDir}{month}{day}{hour}_{pts}.hdr"
                _result_evalglare = shell_evalglare_str, True)
                    dgp=float(_result_evalglare.split()[1])
                    else:
                    _vwrays_str=f"vwrays -ff -x {radiance_param.x_dimension} -y {radiance_param.y_dimension} -vf {config.workDir}view_{pts}.vf | rtrace  -n {opts.c} -ab {opts.ab} -ad {opts.ad} -aa {radiance_param.aa} -as {radiance_param_aS} -lw {radiance_param.lw} -st {radiance_param.st} -ld -ov -ffc $(vwrays -d -x {radiance_param.x_dimension} -y {radiance_param.y_dimension} -vf {config.workDir}view_{pts}.vf) -h+ {workDir}scene.oct | evalglare -vta -vh 180 -vv 180 -vu 0 0 1"
                    _result_vwrays=shell(_vwrays_str, True)
                    dgp=float(_result_vwrays.split()[1])
                    output_file.write(
                f"{month} {day} {hour} {dgp} {illuminance} \n")


                    def annual_eval(outDir, pts):
                    dgp_value=np.genfromtxt("%sdgp_%i.out" % (
                        outDir, pts), delimiter = " ", usecols = 3)
                    fDGPe35=0
                    fDGPe40=0
                    fDGPe45=0
                    for i in range(len(dgp_value)):
                    if dgp_value[i] > 0.35:
                    fDGPe35=fDGPe35 + 1
                    if dgp_value[i] > 0.40:
                    fDGPe40=fDGPe40 + 1
                    if dgp_value[i] > 0.45:
                    fDGPe45=fDGPe45 + 1
                    fDGPe35=fDGPe35 * 5.43 / 1304
                    fDGPe40=fDGPe40 * 5.43 / 1304
                    fDGPe45=fDGPe45 * 5.43 / 1304
                    return [fDGPe35, fDGPe40, fDGPe45]


                    class RadianceParam(object):
                    def __init__(self, opts)
                    self.aa=0.1
                    self.lw=0.002
                    self.st=0.15
                    self.aS=1000
                    self.x_dimension=900
                    self.y_dimension=900
                    self.ab=opts.ab
                    self.ad=opts.ad


                    def write_output(config, cpu_time, fDGPe):
                    file_time=open("%stime.out" % config.outDir, "w")
                    file_time.write("%d %.3f" % (opts.c, cpu_time)
    file_time.close()
    file_fdgpe = open("%sfDGPe_%i.out" % (outDir, pts), "w")
    file_fdgpe.write(fDGPe)
    file_fdgpe.close()


def main(opts, config, radiance_param):
    INOBIS = [4, 4, 4, 4, 4, 3]
    t1 = time.time()
    # view points
    view_points = np.atleast_2d(np.genfromtxt(
        config.viewPoint))  # , delimiter="
    gen_view_file(view_points, workDir)
    # output file
    output_file = open(f"{config.outDir}dgp_{pts}.out")
    fDGPe = ['NaN', 'NaN', 'NaN']
    # static simulation if -date
    if opts.date:
        for pts in range(len(view_points)):
            for i in range(len(opts.date)):
                month = int(opts.date[i][:2])
                day = int(opts.date[i][2:4])
                hour = float(opts.date[i][4:])
                print(month, day, hour)
                calculate_dgp(
                    output_file,
                    month,
                    day,
                    hour,
                    config,
                    opts,
                    radiance_param,
                    pts,
                    flag_direct=1,
                )
    # dynamic simulation
    else:
        for pts in range(len(view_points)):
            for i in range(6):
                month = i + 1
                for j in range(INOBIS[i]):
                    day = j * 7 + 1
                    for k in range(24):
                        hour = k
                        print(month, day, hour)
                        calculate_dgp(
                            output_file,
                            month,
                            day,
                            hour,
                            config,
                            opts,
                            radiance_param,
                            view_points,
                            opts.direct,
                        )
            month = 12
            day = 22
            for k in range(24):
                hour = k
                print(month, day, hour)
                calculate_dgp(
                    output_file,
                    month,
                    day,
                    hour,
                    config,
                    opts,
                    radiance_param,
                    view_points,
                    opts.direct,
                )
            fDGPe = annual_eval(config.outDir, pts)
    t2 = time.time()
    cpu_time = abs(t2 - t1)
    print("CPU time: %.1f s " % cpu_time)
    write_output(config, cpu_time, fDGPe)
    output_file.close()


if __name__ == "__main__":
    try:
        opts = parse_args()
        assert os.path.isfile(opts.config), (
            "Config file '%s' not found" % config_path.split("/")[-1]
        )
        config = parse_config(opts.config)
        radiance_param = RadianceParam(opts)
        _create_non_existing_directories(config)
        main(opts, config, radiance_param)
    except Exception as error:
        print(
            "".join(
                traceback.format_exception(
                    etype=type(error), value=error, tb=error.__traceback__
                )
            )
        )
        sys.exit("The following error occurred: %s" % error)
