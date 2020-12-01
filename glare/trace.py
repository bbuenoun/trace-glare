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
import sys
import traceback
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
    config.work_dir = parser.get("PATHS", "workDir")
    config.out_dir = parser.get("PATHS", "outDir")


def _add_inputs(parser, config):
    config.matFile = parser.get("PATHS", "matFile")
    config.roomFile = parser.get("PATHS", "roomFile")
    config.glazFile = parser.get("PATHS", "glazFile")
    config.shadFile = parser.get("PATHS", "shadFile")
    config.viewPoint = parser.get("PATHS", "viewPoint")
    config.obstacles = parser.get("PATHS", "obstacles")


def _create_non_existing_directories(config):
    if hasattr(config, "out_dir") and not os.path.exists(config.out_dir):
        os.makedirs(config.out_dir)
    if hasattr(config, "work_dir") and not os.path.exists(config.work_dir):
        os.makedirs(config.work_dir)
    if not os.path.isfile("%sskyglowM.rad" % config.work_dir):
        cad = "skyfunc glow groundglow 0 0 4 1 1 1 0 \ngroundglow source ground 0 0 4 0 0 -1 180 \nskyfunc glow skyglow 0 0 4 1 1 1 0 \nskyglow source skydome 0 0 4 0 0 1 180"
        sky_file = open("%sskyglowM.rad" % config.work_dir, "w")
        sky_file.write("%s" % (cad))
        sky_file.close()


def shell(cmd, output_flag=False):
    """ runs shell commands """
    print(cmd)
    stdout = PIPE if output_flag else None
    _completed_process = run(cmd, stdout=stdout, stderr=PIPE, shell=True, check=True)
    if output_flag:
        return _completed_process.stdout.decode("utf-8")


def gen_view_file(view_points, work_dir):
    """ generates view and sensor files from viewPoints """
    sensor_vector = np.zeros(6)
    for i in range(len(view_points)):
        for j in range(6):
            sensor_vector[j] = view_points[i, j]
        with open(f"{work_dir}view_{i}.vf", "w") as view_file:
            view_file.write(
                f"rview -vta -vp {sensor_vector[0]} {sensor_vector[1]} {sensor_vector[2]} -vd {sensor_vector[3]} {sensor_vector[4]} {sensor_vector[5]} -vv 180 -vh 180 -vs 0 -vl 0 -vu 0 0 1\n"
            )
        with open(f"{work_dir}sensor_{i}.pts", "w") as sensor_file:
            sensor_file.write(
                f"{sensor_vector[0]} {sensor_vector[1]} {sensor_vector[2]} {sensor_vector[3]} {sensor_vector[4]} {sensor_vector[5]}\n"
            )


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
    """ runs Radiance to calculate illuminance, dgp and luminance maps """
    # daylight hours
    _sky_str = f"gensky {month} {day} {hour} +s -a {config.lat} -o {config.lon} -m {config.mer}"
    _coordsun = shell(_sky_str, True)
    sun_altitude = float(_coordsun.split()[22])
    if sun_altitude > 0:
        _sky_str = f"gensky {month} {day} {hour} +s -a {config.lat} -o {config.lon} -m {config.mer} > {config.work_dir}sky.rad"
        shell(_sky_str)
        # Radiance octree
        _oct_str = f"oconv {config.work_dir}sky.rad {config.matFile} {config.roomFile} {config.obstacles} {config.shadFile} {config.glazFile} {config.work_dir}skyglowM.rad > {config.work_dir}scene.oct"
        shell(_oct_str)
        # Visible solar disk hours
        _rtrace_str = f"rtrace -h -I -ab 0 -ad {opts.ad} -aa {radiance_param.aa} -as {radiance_param.aS} -lw {radiance_param.lw} -n {opts.c} -ov {config.work_dir}scene.oct <{config.work_dir}sensor_{pts}.pts"
        _rtrace_result = shell(_rtrace_str, True)
        _illuminance_direct = float(_rtrace_result.split()[0]) * 179
        if _illuminance_direct > 0.1 or flag_direct:
            # Point-in-time illuminance calculation
            _rtrace_str = f"rtrace -h -I -ab {opts.ab} -ad {opts.ad} -aa {radiance_param.aa} -as {radiance_param.aS} -lw {radiance_param.lw} -n {opts.c} -ov {config.work_dir}scene.oct <{config.work_dir}sensor_{pts}.pts"
            _rtrace_result = shell(_rtrace_str, True)
            illuminance = float(_rtrace_result.split()[0]) * 179
            # Point-in-time image calculation
            if opts.img:
                _vwrays_str = f"vwrays -ff -x {radiance_param.x_dimension} -y {radiance_param.y_dimension} -vf {config.work_dir}view_{pts}.vf | rtrace  -n {opts.c} -ab {opts.ab} -ad {opts.ad} -aa {radiance_param.aa} -as {radiance_param.aS} -lw {radiance_param.lw} -st {radiance_param.st} -ld -ov -ffc $(vwrays -d -x {radiance_param.x_dimension} -y {radiance_param.y_dimension} -vf {config.work_dir}view_{pts}.vf) -h+ {config.work_dir}scene.oct > {config.out_dir}{month}{day}{hour}_{pts}.hdr"
                shell(_vwrays_str)
                _falsecolor_str = f"falsecolor -ip {config.out_dir}{month}{day}{hour}_{pts}.hdr -l cd/m2 -lw 75 -s 5000 -n 5 | ra_tiff -z - {config.out_dir}{month}{day}{hour}_{pts}.tif"
                shell(_falsecolor_str)
                _evalglare_str = f"evalglare -vta -vh 180 -vv 180 -vu 0 0 1 {config.out_dir}{month}{day}{hour}_{pts}.hdr"
                _result_evalglare = shell(_evalglare_str, True)
                dgp = float(_result_evalglare.split()[1])
            else:
                _vwrays_str = f"vwrays -ff -x {radiance_param.x_dimension} -y {radiance_param.y_dimension} -vf {config.work_dir}view_{pts}.vf | rtrace  -n {opts.c} -ab {opts.ab} -ad {opts.ad} -aa {radiance_param.aa} -as {radiance_param.aS} -lw {radiance_param.lw} -st {radiance_param.st} -ld -ov -ffc $(vwrays -d -x {radiance_param.x_dimension} -y {radiance_param.y_dimension} -vf {config.work_dir}view_{pts}.vf) -h+ {config.work_dir}scene.oct | evalglare -vta -vh 180 -vv 180 -vu 0 0 1"
                _result_vwrays = shell(_vwrays_str, True)
                dgp = float(_result_vwrays.split()[1])
                output_file.write(f"{month} {day} {hour} {dgp} {illuminance} \n")


def annual_eval(out_dir, pts):
    """calculates annual glare metrics """
    dgp_value = np.genfromtxt(f"{out_dir}dgp_{pts}.out", delimiter=" ", usecols=3)
    fdgpe = np.zeros(3)  # DGP > 0.35, 0.4, 0.45
    for i in range(len(dgp_value)):
        for j in range(3):
            if dgp_value[i] > (0.35 + j * 0.05):
                fdgpe[j] = fdgpe[j] + 1
    for j in range(3):
        fdgpe[j] = fdgpe[j] * 5.43 / 1304
    np.savetxt(f"{out_dir}fDGPe_{pts}.out", fdgpe, delimiter=" ", fmt="%1.3f")


class RadianceParam:
    """ Declares Radiance parameters """

    def __init__(self, opts):
        self.aa = 0.1  # pylint: disable=invalid-name
        self.lw = 0.002  # pylint: disable=invalid-name
        self.st = 0.15  # pylint: disable=invalid-name
        self.aS = 1000  # pylint: disable=invalid-name
        self.ab = opts.ab  # pylint: disable=invalid-name
        self.ad = opts.ad  # pylint: disable=invalid-name
        self.x_dimension = 900
        self.y_dimension = 900


def main(opts, config, radiance_param):
    days_per_month = [4, 4, 4, 4, 4, 3]
    start_time = time.time()
    # view points
    view_points = np.atleast_2d(np.genfromtxt(config.viewPoint))  # , delimiter="
    gen_view_file(view_points, config.work_dir)
    # static simulation if -date
    if opts.date:
        for pts in range(len(view_points)):
            output_file = open(f"{config.out_dir}dgp_{pts}.out", "w")
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
            output_file.close()
    # dynamic simulation
    else:
        for pts in range(len(view_points)):
            output_file = open(f"{config.out_dir}dgp_{pts}.out", "w")
            for i in range(6):
                month = i + 1
                for j in range(days_per_month[i]):
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
                            pts,
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
                    pts,
                    opts.direct,
                )
            output_file.close()
            annual_eval(config.out_dir, pts)
    finish_time = time.time()
    cpu_time = abs(finish_time - start_time)
    print("CPU time: %.1f s " % cpu_time)
    file_time = open(f"{config.out_dir}time.out", "w")
    file_time.write(f"{opts.c} {cpu_time}")
    file_time.close()


if __name__ == "__main__":
    try:
        opts = parse_args()
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
