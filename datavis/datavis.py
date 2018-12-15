from pyqtgraph.Qt import QtGui, QtCore
import numpy
import pyqtgraph as pg
from multiprocessing import Process, Manager, Queue
import sched, time, threading
import argparse
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QLabel, QSizePolicy, QSlider, QSpacerItem, \
    QVBoxLayout, QWidget

class Slider(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.horizontalLayout = QHBoxLayout(self)
        self.label = QLabel(self)
        self.horizontalLayout.addWidget(self.label)

        self.slider = QSlider(self)
        self.slider.setOrientation(Qt.Horizontal)
        self.horizontalLayout.addWidget(self.slider)
        """  
        spacerItem1 = QSpacerItem(0, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        """

        self.resize(self.sizeHint())

        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self.setLabelValue)
        self.slider.valueChanged.connect(parent.slider_val_changed)
        self.n=0
        self.setLabelValue(self.slider.value())

    def setLabelValue(self, value):
        self.n = value
        self.label.setText(" %d" % self.n)

class TopLevel(QWidget):
    def __init__(self, rows=1, cols=1,types=dict(), parent=None):
        
        super().__init__(parent=parent)
        ## two types: standard (plots xi vs x_j as selected), full (plots x_i vs timestep - good for llh over time)
        self.rows=rows
        self.cols=cols

        self.types=dict()
        
        for r in range(rows):
            for c in range(cols):
                if((r,c) in types.keys()):
                    self.types[(r,c)]=types[(r,c)]
                else:
                    self.types[(r,c)]="standard"

        ## named dict that contains data in a list, each list item is of dimension n * d (n= num data, d = data dim)
        self.data_storage=dict()
        self.data_dims=dict()
        self.data_dimnames=dict()

        self.plot_handles=dict()
        self.artist_handles=dict()
        self.data_names_per_id=dict()

        ########################

        vlayout = QVBoxLayout(self)
        self.slider=Slider(parent=self)
        vlayout.addWidget(self.slider)
        self.win = pg.GraphicsWindow(title="Basic plotting examples")
        #win.resize(1000,600)
        vlayout.addWidget(self.win)
        self.win.setWindowTitle('pyqtgraph example: Plotting')

        for r in range(self.rows):
            for c in range(self.cols):
                if((r,c) in types.keys()):
                    self.plot_handles[(r,c)] = self.win.addPlot(title="(%d,%d)" % (r,c))
                    self.artist_handles[(r,c)] = self.plot_handles[(r,c)].plot(**types[(r,c)]["kwargs"])
                    self.data_names_per_id[(r,c)]=types[(r,c)]["dataname"]
                else:
                    self.plot_handles[(r,c)] = self.win.addPlot(title="(%d,%d)" % (r,c))
                    self.artist_handles[(r,c)] = self.plot_handles[(r,c)].plot(pen='y')
                    self.data_names_per_id[(r,c)]="data0"
            self.win.nextRow()
        

    def add_data(self, datapoint, name="data0"):

        ## adds data to the data storage 
        if(not name in self.data_storage.keys()):
            
            self.data_storage[name]=[]

            if(len(datapoint.shape)!=2):
                print("data must be of shape nxd (2) but is ", datapoint.shape, " cannot add ...")
                return
            self.data_dims[name]=(datapoint.shape[0], datapoint.shape[1])

        if(datapoint.shape==self.data_dims[name]):
            self.data_storage[name].append(datapoint.copy())
            self.data_updated()
        else:
            print("new datapoint has shape ", datapoint.shape, " but internal data ", name, " has shape ", self.data_dims[name], " cannot add it ...")
            return


    def data_updated(self):
        
        if(len(self.data_storage.keys())>0):
            minlen=99999
            for dname in self.data_storage.keys():
                if(len(self.data_storage[dname])<minlen):
                    minlen=len(self.data_storage[dname])


            self.slider.slider.setMaximum(minlen-1)
            
            self.slider.slider.setValue(minlen-1)

    def slider_val_changed(self, newval):
        
        
        for r in range(self.rows):
            for c in range(self.cols):
                dataname=self.data_names_per_id[(r,c)]
                
                datapointer=self.data_storage[dataname]
                self.artist_handles[(r,c)].setData(datapointer[newval][:,0],datapointer[newval][:,1]) 



class datavis():
    def __init__(self,rows=1,cols=1, types=dict()):
        #threading.Thread.__init__(self)
        self.rows=rows
        self.cols=cols
        self.types=types
        self.visdefs=dict()

        
        
    def start(self):

        self.q = Queue()
        self.p = Process(target=self.run)
        self.p.start()
        return self.q

    def def_vis(self, rowcol, dataname, **kwargs):
        self.visdefs[rowcol] = dict()
        self.visdefs[rowcol]["dataname"]=dataname
        self.visdefs[rowcol]["kwargs"]=kwargs
        
        
    #def join(self):
    #    self.p.join()

    def _update(self):
        if not self.q.empty():
            item = self.q.get()
            if(type(item)==numpy.ndarray):
                self.add_data(item)
            elif(type(item)==list):
                
                if(type(item[0]==numpy.ndarray and type(item[1]==str))):
                    self.add_data(item[0], name=item[1])
            

    def add_data(self, datapoint, name="data0"):
        
        if(self.toplevel is not None):
            
            self.toplevel.add_data(datapoint, name=name)

    def run(self):

        
        self.app = QtGui.QApplication([])
        self.toplevel=TopLevel(rows=self.rows,cols=self.cols,types=self.visdefs)
        self.toplevel.show()
        
        timer = QtCore.QTimer()
        timer.timeout.connect(self._update)
        timer.start(50)

        self.app.exec_()
        

if __name__ == '__main__':

    parser=argparse.ArgumentParser()
    parser.add_argument("file") # numpy array file 
    args=parser.parse_args()


    s = datavis(cols=2)
    #s.def_vis((0,0), "data0", pen=None, symbol='t', symbolPen=None, symbolSize=3, symbolBrush=(255, 0, 0, 200))
    #s.def_vis((0,1), "data0", pen=None, symbol='t', symbolPen=None, symbolSize=5, symbolBrush=(255, 255, 0, 200))
    
   
    dataq=s.start()

    if(os.path.exists(args.file)):
        data=numpy.load(args.file)

        for i in range(data.shape[2]):
            cur_data=data[:,:,i]
            dataq.put([cur_data, "data0"])

            


  