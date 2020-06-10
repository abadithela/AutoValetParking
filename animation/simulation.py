# Automated Valet Parking Simulation Module
# Josefine Graebener, Jiaqi Yan
# California Institute of Technology
# March, 2020

from prepare.boxcomponent import BoxComponent
import trio
import sys
import numpy as np
sys.path.append('..') # enable importing modules from an upper directory
import matplotlib.animation as animation
import matplotlib.pyplot as plt
from animation.helper import draw_car, draw_pedestrian, show_traj
from animation.component import parking_lot
from variables.global_vars import SCALE_FACTOR_SIM, SCALE_FACTOR_PLAN
from variables.parking_data import parking_spots
#from motionplanning.parking_data import parking_spots
from ipdb import set_trace as st
import time
import datetime
import pickle
import os
import warnings

show_all_spots = False
show_trajs = True

ind = 0
warnings.filterwarnings("ignore", category=DeprecationWarning)

class Simulation(BoxComponent):
    def __init__(self):
        super().__init__()
        self.name = self.__class__.__name__
        self.cars = []
        self.peds = []
        self.ax = []
        self.fig = []
        self.background = []
        self.start_walk_lane = (2908,665)
        self.end_walk_lane = (3160,665)
    
    async def add_car_to_sim(self):
        while True:
            async with self.in_channels['Game']:
                async for car in self.in_channels['Game']:
                    print('Simulation System - Adding new car to Map')
                    self.cars.append(car)

    async def rmv_car_from_sim(self):
        while True:
            async with self.in_channels['ExitSim']:
                async for car in self.in_channels['ExitSim']:
                    print('Simulation System - removing car from Map')
                    self.cars.remove(car)

    async def add_ped_to_sim(self):
        while True:
            async with self.in_channels['PedSimulation']:
                async for ped in self.in_channels['PedSimulation']:
                    print('Simulation System - Adding new pedestrian to Map')
                    self.peds.append(ped)
                    #print(self.peds)

    def animate(self, frame_idx): # update animation by dt
        global ind
        ind = ind + 1
        self.ax.clear()
        # scale to the large topo
        xoffset = 0
        yoffset = 0
        f = open('../animation/stored_data/pedestrian_file_new.pkl','ab')
        g = open('../animation/stored_data/car_file_new.pkl','ab')
        pickle.dump('FRAME'+str(ind)+'\n',f)
        for pedestrian in self.peds:
            draw_pedestrian(pedestrian,self.background)
            pickle.dump(pedestrian,f)
        f.close()
        # TO DO figure out how to pickle cars
        # pickle.dump('FRAME'+str(ind)+'\n',g)
        # for car in self.cars: 
        #     draw_car(self.ax,self.background, car.x*SCALE_FACTOR_SIM+xoffset,car.y*SCALE_FACTOR_SIM+yoffset,car.yaw,car)
        #     # draw car trajectories when running sim
        #     if car.ref!= None and show_trajs:
        #         ref = car.ref[car.idx:]
        #         show_traj(self.ax,self.background, ref)
        #     pickle.dump(car,g)
        # g.close()
        
        f = open('../animation/stored_data/car_pos_new.txt','a')
        f.write('FRAME'+str(ind)+'\n')
        for car in self.cars: 
            status = car.status
            if car.parked:
                status = 'Parked'
            if car.requested:
                if car.status=='Stop' or car.status =='Failure':
                    status = car.status
                else:
                    status = 'Requested'
            if car.reserved:
                if car.status=='Stop' or car.status =='Failure':
                    status = car.status
                else:
                    status = 'Reserved'
            draw_car(self.ax,self.background, car.x*SCALE_FACTOR_SIM+xoffset,car.y*SCALE_FACTOR_SIM+yoffset,car.yaw,status,car)
            # draw car trajectories
            if car.ref!= None and show_trajs:
                ref = car.ref[car.idx:]
                show_traj(self.ax,self.background, ref)
            f.writelines([str(car.x),' ', str(car.y),' ', str(car.yaw),' ',str(status), '\n'])
        f.close()
        # to check parking spot locations
        if show_all_spots:
            for key,value in parking_spots.items():
                xd = int(value[0]*SCALE_FACTOR_PLAN*SCALE_FACTOR_SIM+xoffset)
                yd = int(value[1]*SCALE_FACTOR_PLAN*SCALE_FACTOR_SIM+yoffset)
#                print(value[0], value[1])
#                print(xd, yd)
                hd = np.deg2rad(-value[2])
                draw_car(self.ax,self.background,xd,yd,hd,None,None) # without car
        the_parking_lot = [self.ax.imshow(self.background)] # update the stage
        self.background.close()
        self.background = parking_lot.get_background()
        all_artists = the_parking_lot
        return all_artists

    async def update_simulation(self):
        frame_idx = 0
        self.fig = plt.figure()
        new = True
        while True:
            frame_idx +=1 
            #ped = pickle.load( open('pedestrain_file', "rb" ) )\
            if new:
                self.ax = self.fig.add_axes([0,0,1,1]) # get rid of white border
            else:
                self.ax = plt.gca()
            new = False
            plt.axis('off')
            self.background = parking_lot.get_background()
            ani = animation.FuncAnimation(self.fig, self.animate, frames=1, interval=1**3, blit=True, repeat=False)
            plt.pause(0.001)
            plt.draw()
            await trio.sleep(1)
            print('------------Figure updating-------------')

    async def run(self):
        try:
            os.remove("../animation/stored_data/pedestrian_file_new.pkl")
        except:
            print('No file to delete.')
        try:
            os.remove("../animation/stored_data/car_pos_new.txt")
        except:
            print('No file to delete.')
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.add_car_to_sim)
            await trio.sleep(0)
            nursery.start_soon(self.rmv_car_from_sim)
            await trio.sleep(0)
            nursery.start_soon(self.add_ped_to_sim)
            await trio.sleep(0)
            nursery.start_soon(self.update_simulation)
            await trio.sleep(0)
