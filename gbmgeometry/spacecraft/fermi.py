import collections

import healpy as hp
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord

from gbmgeometry.gbm import GBM
from gbmgeometry.utils.array_to_cmap import array_to_cmap
from geometry import Ray
from lat import LAT, LATRadiatorMinus, LATRadiatorPlus
from solar_panels import SolarPanelMinus, SolarPanelPlus


class Fermi(object):
    def __init__(self, quaternion, sc_pos=None):

        # build fermi

        self._lat = LAT()

        self._lat_radiator_plus = LATRadiatorPlus()
        self._lat_radiator_minus = LATRadiatorMinus()

        self._solar_panel_plus = SolarPanelPlus()
        self._solar_panel_minus = SolarPanelMinus()

        self._gbm = GBM(quaternion, sc_pos)

        # grab the frame

        self._frame = self._gbm.n0.center.frame

        # attach the components to fermi

        self._spacecraft_components = collections.OrderedDict()

        self._spacecraft_components[self._lat.name] = self._lat

        self._spacecraft_components[self._lat_radiator_minus.name] = self._lat_radiator_minus
        self._spacecraft_components[self._lat_radiator_plus.name] = self._lat_radiator_plus

        self._spacecraft_components[self._solar_panel_plus.name] = self._solar_panel_plus
        self._spacecraft_components[self._solar_panel_minus.name] = self._solar_panel_minus

        # add lists for each detector to rays

        self._rays = collections.OrderedDict()

        for name in self._gbm.detectors.iterkeys():
            self._rays[name] = []

        self._intersection_points = None

    @property
    def spacecraft_components(self):

        return self._spacecraft_components

    @property
    def rays(self):

        return self._rays

    def add_ray(self, ray_coordinate, probability=None, color='#29FC5C'):

        for name, det in self._gbm.detectors.iteritems():
            ray = Ray(det, ray_coordinate, probability=probability, color=color)

            self._rays[name].append(ray)

    def compute_intersections(self, *detectors):

        self._intersection_points = collections.OrderedDict()

        all_intersections = collections.OrderedDict()

        # go thru all detectors

        if len(detectors) == 0:
            dets = self._rays.keys()

        for det_name, det in self._rays.iteritems():

            self._intersection_points[det_name] = []

            ray_dict = collections.OrderedDict()
            if det_name in dets:

                # now go through all rays

                for i, ray in enumerate(det):

                    # now all components

                    collision_info = collections.OrderedDict()

                    collision_info['surface'] = []
                    collision_info['point'] = []
                    collision_info['distance'] = []

                    for name, component in self._spacecraft_components.iteritems():

                        # intersect the volume with the rays

                        component.intersect_ray(ray)

                        plane, point, distance = component.intersection

                        if plane is not None:
                            collision_info['surface'].append('%s %s' % (name, plane))
                            collision_info['point'].append(point)
                            collision_info['distance'].append(distance)

                            self._intersection_points[det_name].append(point)

                    ray_dict[i] = collision_info

                all_intersections[det_name] = ray_dict

        return all_intersections

    def plot_fermi(self, ax=None, detectors=None, with_rays=False, with_intersections=False):

        if ax is None:

            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')

        else:

            fig = ax.get_figure()

        if detectors is None:

            detectors = self._gbm.detectors.keys()


        else:

            for det in detectors:
                assert det in self._gbm.detectors.keys(), 'invalid detector'

        for name, component in self._spacecraft_components.iteritems():
            component.plot(ax)

        for name, det in self._gbm.detectors.iteritems():

            if name in detectors:
                ax.scatter(*det.mount_point, color='#FFC300')
                ax.text3D(*det.mount_point, s=name)

        if with_rays:

            for name, det in self._rays.iteritems():

                if name in detectors:

                    for ray in det:
                        ray.plot(ax)

        if with_intersections:

            if self._intersection_points is not None:

                for name, points in self._intersection_points.iteritems():
                    if name in detectors:
                        for point in points:
                            ax.scatter(*point, c='r')

        ax.set_xlabel('SCX')
        ax.set_ylabel('SCY')
        ax.set_zlabel('SCZ')

        ax.set_zlim(0, 300)
        ax.set_xlim(-400, 400)
        ax.set_ylim(-400, 400)

        ax.grid(False)
        ax.xaxis.pane.set_edgecolor('black')
        ax.yaxis.pane.set_edgecolor('black')

        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False

        return fig

    def read_healpix_map(self, healpix_map, cmap='viridis'):

        nside = hp.get_nside(healpix_map)

        _, colors = array_to_cmap(healpix_map, cmap=cmap, use_log=False)

        for idx, val in enumerate(healpix_map):

            if val > 0:
                ra, dec = Fermi._pix_to_sky(idx, nside)

                color = colors[idx]

                # now make a point source

                ps = SkyCoord(ra, dec, unit='deg', frame='icrs')

                ps_fermi = ps.transform_to(frame=self._frame)

                self.add_ray(ps_fermi, color=color)

    @staticmethod
    def _pix_to_sky(idx, nside):
        """Convert the pixels corresponding to the input indexes to sky coordinates (RA, Dec)"""

        theta, phi = hp.pix2ang(nside, idx)

        ra = np.rad2deg(phi)
        dec = np.rad2deg(0.5 * np.pi - theta)

        return ra, dec
