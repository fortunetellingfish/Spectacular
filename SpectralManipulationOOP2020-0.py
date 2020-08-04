#View & manipulate spectra, save graphs & sheets
#created by Cassandra Clowe-Coish

import inspect
from enum import Enum

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

from scipy.signal import find_peaks

import tkinter as tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter import ttk
from tkinter import scrolledtext as tkst

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

SOFTWARE_NAME = "Spectacular"
VERSION_NUMBER = "v.0.6.2"

#=================================================================================================================================================
class Minerals(Enum):
    CALCITE = ([875, 1420, 713], True)
    ARAGONITE = ([713,860,1500], True)

    def __init__(self, peaks, isGrindable):
        self.peaks = peaks
        self.isGrindable = isGrindable
                 
#===================================================================================================================================
class App(tk.Tk): ###The controller of all pages, & control of operations
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {} #holds the app's pages

        self.dfs = {}  #contains dataframes loaded from csv/made by the user
        self.spectra = {} #contains spectrum objects
        self.plots = {} #contains Figure objects. Each figure can have exactly one axis

        self.filetypes = {'csv':pd.read_csv,
                          'fwf':pd.read_fwf} #the file types and pandas method references
        
        for F in (HomePage, SpectraPage, GraphPage, MakeSpectrumPage, TutorialPage):
            frame = F(container, self)
            self.frames[F] = frame

            self.wm_title(SOFTWARE_NAME + " " + VERSION_NUMBER)
         #   self.iconphoto(True, tk.PhotoImage(file='icon.png'))
            
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(HomePage)

    def show_frame(self, cont):
        self.frames[cont].tkraise()

    def updatePages(self):
        for Page in {MakeSpectrumPage, SpectraPage}:
            self.frames[Page].insertItems()

    def load(self, filename, filetype, delimiter=None): #load csv file
        try:
            df = self.filetypes[filetype](filename, thousands=" ", delimiter=delimiter, header=None)
            if any(df.iloc[0].apply(lambda x: isinstance(x, str))): #if the csv file has column names already
                df = df[1:].reset_index(drop=True).rename(columns=df.iloc[0]).apply(pd.to_numeric, axis=1)
            else: #give the DataFrame default column names
                names=[]
                for i in range(len(df.columns)):
                    names.append("w%i" %i)
                df.columns = names
            self.dfs[filename] = df
            self.updatePages()
 
        except pd.errors.ParserError:
            raise UnsupportedFileTypeException(filename)
        except FileNotFoundError as not_found:
            raise NoPathNameException(not_found)

    def save(self, key, savefilename):
        self.spectra[key].df.to_csv(savefilename)

    def get_dfs(self):
        return self.dfs

    def get_spectra(self):
        return self.spectra

    def get_plots(self):
        return self.plots

    def rename_plot(self, oldKey, newKey):
        self.plots[newKey] = self.plots.pop(oldKey)

    def make_spectrum(self, name, df, x, y): #create a Spectrum object and add it to dictionary
        spectrum = Spectrum(name, df, x, y)
        self.spectra[name] = spectrum
        self.updatePages()
        return spectrum

    def make_plot(self, name):
        fig = Figure(figsize=(8.5, 5.5), dpi=100)
        fig.suptitle(name)
        axis = fig.add_subplot(111)
        self.plots[name] = fig

    def delete_spectrum(self, name):
        del self.spectra[name]
        self.frames[SpectraPage].insertItems()

    def delete_plot(self, name):
        plt.close(self.plots.pop(name))

    def graph(self, axis, spectrum, **kwargs):
        axis.plot(spectrum.xdata, spectrum.ydata, label=spectrum.name, **kwargs)

    def operation(self, Class, operationName, name, *args, **kwargs):
        #perform an operation on spectral operands and format them & send to a Spectrum object
        #operate on operands only if their x axes are identical
        if all(isinstance(arg, Spectrum) for arg in args):
            if all(arg.xdata.equals(args[0].xdata) for arg in args):
                print(args)
                df = getattr(Class, operationName)(*args, **kwargs)
                return self.make_spectrum(name, df, df.columns[0], df.columns[1])
            else: raise BadAxisSymmetryException
        else: raise ValueError

#=====================================================================================================================================================================================
class SpectrumOperations:
#operations whose operands are spectra only
    @classmethod
    def add(self, s1, s2):
        return pd.concat([s1.xdata, s1.ydata + s2.ydata], axis=1)

    @classmethod
    def subtract(self, s1, s2):
        return pd.concat([s1.xdata, s1.ydata - s2.ydata], axis=1)
        
    @classmethod
    def multiply(self, s1, s2):
        return pd.concat([s1.xdata, s1.ydata * s2.ydata], axis=1)

    @classmethod
    def divide(self, s1, s2):
        return pd.concat([s1.xdata, s1.ydata / s2.ydata], axis=1)

    @classmethod
    def to_transmittance(self, spectrum):
        return pd.concat([spectrum.xdata, 100*(10**(-spectrum.ydata))], axis=1)

    @classmethod
    def to_absorption(self, spectrum):
        return pd.concat([spectrum.xdata, -np.log10(spectrum.ydata)], axis=1)

#==========================================================================================================================================================================================
class ParameterisedOperations:
    @classmethod
    def zero(cls, spectrum, leftidx=0, rightidx=0): #zero the spectrum between two indices
        y = spectrum.ydata
        y[leftidx:rightidx] = 0
        return pd.concat([spectrum.xdata, y], axis=1)
    
    @classmethod
    def grinding_curve(cls, *args, mineral=Minerals.CALCITE):
        #@param guesses an ordered list of wavenumbers where the peaks are likely to be found
        #@param *args the spectra from which to construct the curve
        if mineral.isGrindable:
            points=[] #list of tuples[(v2/v3, v4/v3)]
            for arg in args:
                maxima = []
                for guess in mineral.peaks:
                    maxima.append(Transformations.find_maximum(arg, guess)[1])
                largest = maxima.pop(maxima.index(max(maxima))) # get the largest peak and remove it from list
                points.append((maxima[0]/largest, maxima[1]/largest))
            return pd.DataFrame(points, columns=["v2/v3", "v4/v3"])
    
#==========================================================================================================================================================================================
class Transformations:
#a group of functions which returns a non-curve (non DataFrame) result
    @classmethod
    def find_maximum(cls, spectrum, guess=None):
        #if no guess is provided, the global maximum will be returned
        if(guess):
            peaks, _ = find_peaks(spectrum.ydata.values)# returns array of indices
            peakpts = spectrum.df.iloc[peaks].reset_index()
            closest = peakpts.iloc[[(peakpts.iloc[:,1]-guess).abs().argsort()[0]]]
            return (closest.iat[0,1], closest.iat[0,2])
        else:
            return (spectrum.xdata[spectrum.ydata.idxmax()], spectrum.ydata.max())

#==========================================================================================================================================================================================
class AppPage(tk.Frame):
    HOMEPAGE_TEXT = "Back to Home"
    MAKESPECTRUMPAGE_TEXT = "Create Spectrum from File"
    SPECTRAPAGE_TEXT = "Spectra Page"
    GRAPHPAGE_TEXT = "Graph Page"
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.navigationTray = tk.Frame(self, borderwidth=2, relief=tk.GROOVE)
        self.widgetFrame = tk.Frame(self, borderwidth=2, relief=tk.GROOVE)
        self.alertBox = tk.Label(self)
        self.pageLabel = tk.Label(self.navigationTray)

        self.navigationTray.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky='nsew')
        self.pageLabel.grid(row=0, column=0, sticky='nsew')
        self.widgetFrame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
        self.alertBox.grid(row=1, column=1, sticky='ew')

        self.makeWidgets()

        self.columnconfigure(1, weight=2)
        for j in range(self.grid_size()[1]): #for however many rows there are
            self.rowconfigure(j, weight=1)

    def makeWidgets(self):
        self.makeNavigationButtons()

    def makeNavigationButtons(self):
        pass

#==========================================================================================================================================================================================
class HomePage(AppPage): #### The homepage of the application
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.welcomeMessage = "Welcome to " + SOFTWARE_NAME + " " + VERSION_NUMBER
        self.pageLabel.configure(text="Home Page")
        self.alertBox.configure(text=self.welcomeMessage)
        
        self.widgetFrame.grid(row=0, column=1, sticky='')

    def makeWidgets(self):
        super().makeWidgets()
        loadCSVButton = ttk.Button(self.widgetFrame, text="Load delimited file", command=self.loadDelimited)
        loadCSVButton.grid(row=0, column=0, sticky='ew')

        loadFWFButton = ttk.Button(self.widgetFrame, text="Load Fixed Width", command=lambda:1+1)
        
        makeSpectrumPageButton = ttk.Button(self.widgetFrame, text=AppPage.MAKESPECTRUMPAGE_TEXT, command=lambda:self.controller.show_frame(MakeSpectrumPage))
        makeSpectrumPageButton.grid(row=2, column=0, sticky='ew')

    def makeNavigationButtons(self):
        tutorialButton = ttk.Button(self.navigationTray, text="Tutorial", command=lambda:self.controller.show_frame(TutorialPage))
        tutorialButton.grid(row=1, column=0, padx=10, sticky='nsew')
        
        spectraPageButton = ttk.Button(self.navigationTray, text=AppPage.SPECTRAPAGE_TEXT, command=lambda:self.controller.show_frame(SpectraPage))
        spectraPageButton.grid(row=2, column=0, padx=10, sticky='nsew')

        graphPageButton = ttk.Button(self.navigationTray, text=AppPage.GRAPHPAGE_TEXT, command=lambda:self.controller.show_frame(GraphPage))
        graphPageButton.grid(row=3, column=0, padx=10, sticky='nsew')

    def loadDelimited(self):
        try:
            LoadDelimitedFilePopup(self)
        
        except NoPathNameException as inst:
            self.alertBox.configure(text=inst.message)

#=================================================================================================================================================
class MakeSpectrumPage(AppPage):
###Page which allows the user to make a new Spectrum object from one of the loaded files.
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller=controller

        self.filenameVar = tk.StringVar()
        self.nameVar = tk.StringVar()
        self.xVar = tk.StringVar()
        self.yVar = tk.StringVar()

        super().__init__(parent, controller)

        self.filenameVar.trace('w', self.filenameSelected)
        self.nameVar.trace('w', self.activateCreate)
        self.xVar.trace('w', self.activateCreate)
        self.yVar.trace('w', self.activateCreate)

        self.pageLabel.configure(text=AppPage.MAKESPECTRUMPAGE_TEXT)

    def makeWidgets(self):
        #make the create spectrum button
        self.createButton = ttk.Button(self.widgetFrame, text="Create Spectrum", command=self.makeSpectrum, state='disabled')
        self.createButton.grid(row=3, column=1, sticky='w', padx=10, pady=10)

        #name entry and label
        nameLabel = tk.Label(self.widgetFrame, text="Spectrum Name:").grid(row=0, column=0, padx=10, pady=10)
        nameEntry = ttk.Entry(self.widgetFrame, textvariable=self.nameVar)
        nameEntry.grid(row=0, column=1, sticky='w', padx=10, pady=10)
        nameEntry.insert('end', 'NewSpectrum')

        #make source file chooser & label
        fileLabel = tk.Label(self.widgetFrame, text="Source File:").grid(row=1, column=0, padx=10, pady=10)
        self.fileCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(self.controller.get_dfs().keys()), textvariable=self.filenameVar, width=70)
        self.fileCombobox.grid(row=1, column=1, padx=10, pady=10, sticky='ew')

        #Make a scrollable widget to preview the csv file
        self.previewContainer = tk.Frame(self.widgetFrame, relief=tk.GROOVE)
        self.previewContainer.grid(row=0, column=2, padx=10, pady=10, sticky='nsew', rowspan=3)
        
        self.dfPreview = tk.Text(self.previewContainer, state='disabled', width=50, wrap='none')
        self.dfPreview.grid(row=1, column=0)

        vscrollbar = ttk.Scrollbar(self.previewContainer, orient='vertical', command=self.dfPreview.yview)
        hscrollbar = ttk.Scrollbar(self.previewContainer, orient='horizontal', command=self.dfPreview.xview)
        self.dfPreview.configure(yscrollcommand=vscrollbar.set, xscrollcommand=hscrollbar.set)
        vscrollbar.grid(row=1, column=1, sticky='ns')
        hscrollbar.grid(row=2, column=0, sticky='ew')
        
        previewLabel = tk.Label(self.previewContainer, text="Preview:")
        previewLabel.grid(row=0, column=0, padx=10, sticky='sw')
        
        #make tray to hold the fields and their labels
        axesTray = tk.Frame(self.widgetFrame)
        axesTray.grid(row=2, column=0, columnspan=2)
        
        #Make entry fields for the x and y coordinates of the new spectrum
        self.xField = ttk.Combobox(axesTray, state='disabled', textvariable=self.xVar)
        self.xField.grid(row=0, column=1, sticky='w', padx=5, pady=10)
        xLabel = tk.Label(axesTray, text="X Column").grid(row=0, column=0, padx=5, sticky='ew')
        
        self.yField = ttk.Combobox(axesTray, state='disabled', textvariable=self.yVar)
        self.yField.grid(row=0, column=3, sticky='w', padx=5, pady=10)
        yLabel = tk.Label(axesTray, text="Y Column").grid(row=0, column=2, sticky='ew', padx=5)

        super().makeWidgets()

    def makeNavigationButtons(self):
        #make page navigation Buttons
        homePageButton = ttk.Button(self.navigationTray, text=AppPage.HOMEPAGE_TEXT, command=lambda: self.controller.show_frame(HomePage))
        homePageButton.grid(row=1, column=0, padx=10, sticky='nsew')

        spectraPageButton = ttk.Button(self.navigationTray, text=AppPage.SPECTRAPAGE_TEXT, command=lambda: self.controller.show_frame(SpectraPage))
        spectraPageButton.grid(row=2, column=0, padx=10, sticky='nsew')

        graphPageButton = ttk.Button(self.navigationTray, text=AppPage.GRAPHPAGE_TEXT, command=lambda: self.controller.show_frame(GraphPage))
        graphPageButton.grid(row=3, column=0, padx=10, sticky='nsew')

    def insertItems(self):
        #Populate the file list with keys from the App's file/dataframe dictionary
        self.fileCombobox.configure(values=list(self.controller.get_dfs().keys()))

    def filenameSelected(self, *args):
        if self.filenameVar.get():
            #activate xy fields
            self.xField.configure(values=list(self.controller.get_dfs()[self.filenameVar.get()].columns), state='readonly')
            self.yField.configure(values=list(self.controller.get_dfs()[self.filenameVar.get()].columns), state='readonly')
            self.xField.set("")
            self.yField.set("")
            #show preview & disable the textbox
            self.dfPreview.configure(state='normal')
            self.dfPreview.delete(1.0, 'end')
            self.dfPreview.insert('end', str(self.controller.get_dfs()[self.filenameVar.get()]))
            self.dfPreview.configure(state='disabled')

    def activateCreate(self, *args):
        #make the Create button active when all fields are filled
        self.createButton.configure(state='disabled')
        if (self.nameVar.get() and self.xVar.get() and self.yVar.get()):
            self.createButton.configure(state='normal')

    def makeSpectrum(self):
        #make a Spectrum object
        try:
            self.controller.make_spectrum(self.nameVar.get(), self.controller.get_dfs()[self.filenameVar.get()], self.xVar.get(), self.yVar.get())
            self.alertBox.config(text="Spectrum added to list.")

        except KeyError:
            self.alertBox.configure(text="Please fill out all fields")
        except BadAxisSymmetryException as inst:
            self.alertBox.configure(text=inst.message)
        finally:
            self.after(5000, lambda:self.alertBox.configure(text=""))

#=============================================================================================================================================        
class SpectraPage(AppPage):
    def __init__(self, parent, controller):
        self.spectrumVar = tk.StringVar()
        self.dfVar = tk.StringVar()

        super().__init__(parent, controller)
        
        self.spectrumVar.trace('w', self.updateTableViewer)
        self.dfVar.trace('w', self.updateTableViewer)

        self.pageLabel.configure(text="Spectra Page")

    def makeNavigationButtons(self):
        homePageButton = ttk.Button(self.navigationTray, text=AppPage.HOMEPAGE_TEXT, command=lambda:self.controller.show_frame(HomePage))
        homePageButton.grid(row=1, column=0, padx=10, sticky='nsew')
        graphPageButton = ttk.Button(self.navigationTray, text=AppPage.GRAPHPAGE_TEXT, command=lambda:self.controller.show_frame(GraphPage))
        graphPageButton.grid(row=2, column=0, padx=10, sticky='nsew')

    def makeWidgets(self):
        super().makeWidgets()
        spectraTray = tk.Frame(self.widgetFrame, width=30)
        spectraTray.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

        ##make the spectra list
        spectraLabel = tk.Label(spectraTray, text="Spectra")
        spectraLabel.grid(row=1, column=0, sticky='ew', padx=3, pady=10)
        self.spectraCombobox = ttk.Combobox(spectraTray, state='readonly', textvariable=self.spectrumVar)
        self.spectraCombobox.grid(row=2, column=0, columnspan=2, sticky='ew', padx=3, pady=10)

        #make the container for spectra buttons
        buttonTray = tk.Frame(spectraTray)
        buttonTray.grid(row=3, column=0, pady=10, sticky='nsew')

        #make spectra manipulation buttons
        duplicateButton = ttk.Button(buttonTray, text="Duplicate", command=lambda:DuplicateSpectrumPopup(self))
        duplicateButton.grid(row=0, column=0, sticky='nsew')

        deleteButton = ttk.Button(buttonTray, text="Delete", command=lambda:DeleteSpectrumPopup(self))
        deleteButton.grid(row=1, column=0, sticky='nsew')

        saveButton = ttk.Button(buttonTray, text="Save", command=lambda:SaveSpectrumPopup(self))
        saveButton.grid(row=2, column=0, sticky='nsew')

        arithmeticButton = ttk.Button(buttonTray, text="Arithmetic", command=lambda:ArithmeticPopup(self))
        arithmeticButton.grid(row=0, column=1, sticky='nsew')

        grindingCurveButton = ttk.Button(buttonTray, text="Grinding Curve", command=lambda:GrindingCurvePopup(self))
        grindingCurveButton.grid(row=1, column=1, sticky='nsew')

        zeroButton = ttk.Button(buttonTray, text="Zero Spectrum", command=lambda:ZeroSpectrumPopup(self))
        zeroButton.grid(row=2, column=1, sticky='nsew')

        #make df list
        tk.Label(spectraTray, text="Files").grid(row=4, column=0, sticky='ew', padx=3, pady=10)
        self.dfCombobox = ttk.Combobox(spectraTray, state='readonly', textvariable=self.dfVar)
        self.dfCombobox.grid(row=5, column=0, sticky='ew', columnspan=2, padx=3, pady=10)

        #make widget to view data
        tableViewerContainer = tk.Frame(self.widgetFrame)
        tableViewerContainer.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')

        self.viewerLabel = tk.Label(tableViewerContainer, text="Data", width=120)
        self.viewerLabel.grid(row=0, column=0)

        self.tableViewer = tk.Text(tableViewerContainer, state='disabled', bg='white', width=50, height=35, wrap='none')
        self.tableViewer.grid(row=1, column=0, sticky='nsew')

        vscrollbar = ttk.Scrollbar(tableViewerContainer, orient='vertical', command=self.tableViewer.yview)
        hscrollbar = ttk.Scrollbar(tableViewerContainer, orient='horizontal', command=self.tableViewer.xview)
        self.tableViewer.configure(yscrollcommand=vscrollbar.set, xscrollcommand=hscrollbar.set)
        vscrollbar.grid(row=1, column=1, sticky='ns')
        hscrollbar.grid(row=2, column=0, sticky='ew')
        
    def updateTableViewer(self, *args):
        self.tableViewer.configure(state='normal')
        self.tableViewer.delete(1.0, 'end')
        if self.spectrumVar.get():
            self.tableViewer.insert(tk.INSERT, self.controller.get_spectra()[self.spectraCombobox.get()].df)
            self.viewerLabel.configure(text=self.spectrumVar.get())
            self.spectraCombobox.set('')
        if self.dfVar.get():
            self.tableViewer.insert(tk.INSERT, self.controller.get_dfs()[self.dfVar.get()])
            self.viewerLabel.configure(text=self.dfVar.get())
            self.dfCombobox.set('')
        self.tableViewer.configure(state='disabled')

    def insertItems(self):
        self.spectraCombobox.set('')
        self.spectraCombobox.configure(values=list(self.controller.get_spectra().keys()))
        self.dfCombobox.set('')
        self.dfCombobox.configure(values=list(self.controller.get_dfs().keys()))

#===================================================================================================================================
class GraphPage(AppPage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        self.controller.make_plot('Plot 1')
        self.showFigure(self.controller.get_plots()['Plot 1'])
        self.pageLabel.configure(text="Graph Page")

    def makeWidgets(self):
        #make container for graph/trace modification buttons
        self.graphTray = tk.Frame(self.widgetFrame, width=50, borderwidth=2, relief=tk.RAISED)
        self.graphTray.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')

        addTraceButton = ttk.Button(self.graphTray, text="Add Trace", command=lambda:AddTracePopup(self)).grid(row=0, column=0, sticky='nsew')
        deleteTraceButton = ttk.Button(self.graphTray, text="Delete Trace", command=lambda:DeleteTracePopup(self)).grid(row=1, column=0, sticky='nsew')
        modifyTraceButton = ttk.Button(self.graphTray, text="Modify Trace", command=lambda:ModifyTracePopup(self)).grid(row=2, column=0, sticky='nsew')
    
        updateLegendButton = ttk.Button(self.graphTray, text="Update Legend", command=self.updateLegend).grid(row=4, column=1, sticky='nsew')

        newPlotButton = ttk.Button(self.graphTray, text="New Plot", command=lambda:NewPlotPopup(self)).grid(row=0, column=1, sticky='nsew')
        deletePlotButton = ttk.Button(self.graphTray, text="Delete Plot", command=lambda:DeletePlotPopup(self)).grid(row=1, column=1, sticky='nsew')
        modifyPlotButton = ttk.Button(self.graphTray, text="Modify Plot", command=lambda:ModifyPlotPopup(self)).grid(row=2, column=1, sticky='nsew')
        showPlotButton = ttk.Button(self.graphTray, text="Show Plot", command=lambda:ShowPlotPopup(self)).grid(row=3, column=1, sticky='nsew')

        super().makeWidgets()
            
    def showFigure(self, fig):
        if hasattr(self, 'toolbar_frame'):
            self.toolbar_frame.destroy()

        self.canvas = FigureCanvasTkAgg(fig, self.widgetFrame)
        self.canvas._tkcanvas.grid(row=0, column=0, padx=10, pady=10, rowspan=2, columnspan=2)
        self.toolbar_frame = tk.Frame(self.widgetFrame)
        self.toolbar_frame.grid(row=2, column=0, padx=10, pady=10, columnspan=2)

        toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame)
        toolbar.update()
        self.canvas.draw()

    def makeNavigationButtons(self):
        homePageButton = ttk.Button(self.navigationTray, text=AppPage.HOMEPAGE_TEXT, command=lambda:self.controller.show_frame(HomePage))
        homePageButton.grid(row=1, column=0, padx=10, sticky='nsew')
        spectraPageButton = ttk.Button(self.navigationTray, text=AppPage.SPECTRAPAGE_TEXT, command=lambda:self.controller.show_frame(SpectraPage))
        spectraPageButton.grid(row=2, column=0, padx=10, sticky='nsew')

    def updateLegend(self):
        self.canvas.figure.axes[0].legend()
        self.canvas.draw()

#=======================================================================================================================================================================================================================
class TutorialPage(AppPage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        self.pageLabel.configure(text="Tutorial")

        self.gettingStartedText = ""
        self.makeSpectrumText = ""
        self.spectraText = ""
        self.graphText = ""

    def makeWidgets(self):
        tutorialBox = tk.Text(self.widgetFrame, state='disabled', bg='white', width=50, height=35)
        tutorialBox.grid(row=0, column=0, sticky='nsew')
        vscrollbar = ttk.Scrollbar(tutorialBox, orient='vertical', command=tutorialBox.yview)
        vscrollbar.grid(row=0, column=1, sticky='ns')
        super().makeWidgets()

    def makeNavigationButtons(self):
        homePageButton = ttk.Button(self.navigationTray, text=AppPage.HOMEPAGE_TEXT, command=lambda:self.controller.show_frame(HomePage))
        homePageButton.grid(row=1, column=0, padx=10, sticky='nsew')

        spectraPageButton = ttk.Button(self.navigationTray, text=AppPage.SPECTRAPAGE_TEXT, command=lambda:self.controller.show_frame(SpectraPage))
        spectraPageButton.grid(row=2, column=0, padx=10, sticky='nsew')

        graphPageButton = ttk.Button(self.navigationTray, text=AppPage.GRAPHPAGE_TEXT, command=lambda:self.controller.show_frame(GraphPage))
        graphPageButton.grid(row=3, column=0, padx=10, sticky='nsew')

        makeSpectrumPageButton = ttk.Button(self.navigationTray, text=AppPage.MAKESPECTRUMPAGE_TEXT, command=lambda:self.controller.show_frame(MakeSpectrumPage))
        makeSpectrumPageButton.grid(row=4, column=0, padx=10, sticky='nsew')
#=======================================================================================================================================================================================================================
class Spectrum: #Objects of this class are two-column structures.
    def __init__(self, name, sourcedf, x, y):
        self.xdata = sourcedf[x]
        self.ydata = sourcedf[y]
        self.df = pd.concat([self.xdata, self.ydata], axis=1)
        self.name = name
        if self.xdata.dropna().size != self.ydata.dropna().size:
            raise BadAxisSymmetryException()

#=======================================================================================================================================================================================================================
class ConditionalPopup(tk.Toplevel):
    #parent class of OK/Cancel popups where OK is disabled until all fields are filled
    def __init__(self, master, title, **kwargs):#@param **kwargs the Variables traced by the widgets in the popup
        if all(isinstance(kwarg, tk.Variable) for kwarg in kwargs.values()):
            super().__init__(master)
            self.__dict__.update(kwargs)
            self.master = master
            self.vars = kwargs #dictionary of kwargs
            
            self.wm_title(title)

            self.widgetFrame = tk.Frame(self)
            self.widgetFrame.grid(row=0, column=0)

            self.makeWidgets()
            self.traceVars()
            
        else: raise TypeError
       
    def traceVars(self):
        #attach the activateOK method to the textvariables of the popup
        for var in self.vars.values():
            var.trace('w', self.activateOK)

    def activateOK(self, *args):
        self.okButton.configure(state='disabled')
        if all(self.vars[key].get() for (key, value) in self.vars.items()):
            self.okButton.configure(state='normal')

    def makeWidgets(self):
        self.okButton = ttk.Button(self, text="OK", state='disabled', command=self.okPressed)
        self.okButton.grid(row=self.grid_size()[1], column=0, padx=2.5, pady=10, sticky='e')
        cancelButton = ttk.Button(self, text="Cancel", command=self.destroy)
        cancelButton.grid(row=self.okButton.grid_info()['row'], column=1, padx=2.5, pady=10, sticky='w')

    def makeAlertBox(self):
        self.alertBox = tk.Label(self)
        self.alertBox.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky='ew')

    def okPressed(self, *args):
        self.destroy()

#===========================================================================================================================================================================================================================
class GraphPopup(ConditionalPopup):
    def okPressed(self, *args):
        self.master.canvas.draw()
        super().okPressed()

#===========================================================================================================================================================================================================================
class LoadDelimitedFilePopup(ConditionalPopup):
    def __init__(self, master):
        self.delimiters={'comma':',',
                         'tab':'\t',
                         'space':' ',
                         'newline':'\n'} #map delimiter names to their str representations

        super().__init__(master, "Load Delimited File", filenameVar=tk.StringVar(),
                                                           delimiterVar=tk.StringVar())
        
    def makeWidgets(self):
        fileChooserButton = ttk.Button(self.widgetFrame, text="Choose File", command=self.getfilename)
        fileChooserButton.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

        delimiterCombobox = ttk.Combobox(self.widgetFrame, values=list(self.delimiters.keys()), textvariable=self.delimiterVar)
        delimiterCombobox.set("Select a delimiter")
        delimiterCombobox.configure(state='readonly')
        delimiterCombobox.grid(row=1, column=0, padx=10, pady=10, sticky='nsew')

        self.makeAlertBox()
        super().makeWidgets()

    def getfilename(self):
        self.filenameVar.set(askopenfilename())

    def okPressed(self, *args):
        try:
            self.master.controller.load(self.filenameVar.get(), 'csv', delimiter=self.delimiters[self.delimiterVar.get()])
            super().okPressed()
            
        except UnsupportedFileTypeException as inst:
            self.alertBox.configure(text=inst.message)
            self.after(3000, lambda:self.alertBox.configure(text=""))

#===========================================================================================================================================================================================================================
class DuplicateSpectrumPopup(ConditionalPopup):
    def __init__(self, master):
        super().__init__(master, "Duplicate Spectrum", nameVar=tk.StringVar(),
                                                         spectrumVar=tk.StringVar())
    def makeWidgets(self):
        #name label and entry
        nameLabel = tk.Label(self.widgetFrame, text="Name the new spectrum:")
        nameLabel.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        nameEntry = ttk.Entry(self.widgetFrame, textvariable=self.nameVar)
        nameEntry.grid(row=0, column=1, padx=10, pady=10, sticky='w')
        
        spectrumLabel = tk.Label(self.widgetFrame, text="Source:")
        spectrumLabel.grid(row=1, column=0, padx=10, pady=10, sticky='e')
        spectrumCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(self.master.controller.get_spectra().keys()), textvariable=self.spectrumVar)
        spectrumCombobox.grid(row=1, column=1, padx=10, pady=10, sticky='w')

        self.makeAlertBox()
        super().makeWidgets()

    def okPressed(self, *args):
        if self.nameVar.get() == self.spectrumVar.get():
            self.alertBox.configure(text="Names cannot be the same!")
        else:
            self.master.controller.make_spectrum(self.nameVar.get(), self.master.controller.get_spectra()[self.spectrumVar.get()].df, self.master.controller.get_spectra()[self.spectrumVar.get()].df.columns[0], self.master.controller.get_spectra()[self.spectrumVar.get()].df.columns[1])
            super().okPressed()

#=====================================================================================================================================================================================================================================================================================================
class DeleteSpectrumPopup(ConditionalPopup):
    def __init__(self, master):
        super().__init__(master, "Delete Spectrum", spectrumVar=tk.StringVar())

    def makeWidgets(self):
        #spectra label and combobox
        spectrumVar = tk.Label(self.widgetFrame, text="Spectrum:")
        spectrumVar.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        
        spectrumCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(self.master.controller.get_spectra().keys()), textvariable=self.spectrumVar)
        spectrumCombobox.grid(row=0, column=1, padx=10, pady=10, sticky='w')

        super().makeWidgets()

    def okPressed(self, *args):
        self.master.controller.delete_spectrum(self.spectrumVar.get())
        self.master.insertItems()
        super().okPressed()

#=====================================================================================================================================================================================================================================================================================================
class SaveSpectrumPopup(ConditionalPopup):
    def __init__(self, master):
        super().__init__(master, "Save Spectrum", spectrumVar=tk.StringVar())

    def makeWidgets(self):
        #spectrum label and combobox
        spectrumLabel = tk.Label(self.widgetFrame, text="Spectrum:")
        spectrumLabel.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        spectrumCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(self.master.controller.get_spectra().keys()), textvariable=self.spectrumVar)
        spectrumCombobox.grid(row=0, column=1, padx=10, pady=10, sticky='w')
        super().makeWidgets()

    def okPressed(self, *args):
        self.master.controller.save(self.spectrumVar.get(), asksaveasfilename())

#=====================================================================================================================================================================================================================================================================================================
class AddTracePopup(GraphPopup):
    #a popup that enables adding a trace to a chosen plot
    def __init__(self, master):
        super().__init__(master, "Add trace to plot",
                         plotVar=tk.StringVar(),
                         spectrumVar=tk.StringVar(),
                         colorVar=tk.StringVar(),
                         linewidthVar=tk.StringVar())


    def activateOK(self, *args):
        if self.linewidthVar.get().isdecimal():
            super().activateOK(*args)

    def makeWidgets(self):
        #plot label and combobox
        plotLabel = tk.Label(self.widgetFrame, text="Plot:")
        plotLabel.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        plotCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(self.master.controller.get_plots().keys()), textvariable=self.plotVar)
        plotCombobox.grid(row=0, column=1, padx=10, pady=10, sticky='w')

        #spectrum label and combobox
        spectrumLabel = tk.Label(self.widgetFrame, text="Spectrum:")
        spectrumLabel.grid(row=1, column=0, padx=10, pady=10, sticky='e')
        spectrumCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(self.master.controller.get_spectra().keys()), textvariable=self.spectrumVar)
        spectrumCombobox.grid(row=1, column=1, padx=10, pady=10, sticky='w')

        #colour label and combobox
        colourLabel = tk.Label(self.widgetFrame, text="Colour:")
        colourLabel.grid(row=2, column=0, padx=10, pady=10, sticky='e')
        colourCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(mcolors.CSS4_COLORS), textvariable=self.colorVar)
        colourCombobox.grid(row=2, column=1, padx=10, pady=10, sticky='w')

        #linewidth label and entry
        linewidthLabel = tk.Label(self.widgetFrame, text="Line width:")
        linewidthLabel.grid(row=3, column=0, padx=10, pady=10, sticky='e')
        linewidthEntry = ttk.Entry(self.widgetFrame, textvariable=self.linewidthVar)
        linewidthEntry.grid(row=3, column=1, padx=10, pady=10, sticky='w')

        self.makeAlertBox()
        super().makeWidgets()

    def okPressed(self, *args):
        try:
            self.master.controller.graph(self.master.controller.get_plots()[self.plotVar.get()].axes[0],
                                            self.master.controller.get_spectra()[self.spectrumVar.get()],
                                            color=self.colorVar.get(),
                                            linewidth=float(self.linewidthVar.get()))
            
            super().okPressed()
        except ValueError:
            self.alertBox.configure(text="Line width must be numeric.")

#=========================================================================================================================================================
class DeleteTracePopup(GraphPopup):
    def __init__(self, master):
        super().__init__(master, "Delete trace", plotNameVar=tk.StringVar(),
                                                 traceVar=tk.StringVar())

    def traceVars(self):
        super().traceVars()
        self.plotNameVar.trace('w', self.activateTraceField)

    def makeWidgets(self):
        #plot label and combobox
        plotLabel = tk.Label(self.widgetFrame, text="Plot:")
        plotLabel.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        plotCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(self.master.controller.get_plots().keys()), textvariable=self.plotNameVar)
        plotCombobox.grid(row=0, column=1, padx=10, pady=10, sticky='w')

        #trace label and combobox
        traceLabel = tk.Label(self.widgetFrame, text="Trace:")
        traceLabel.grid(row=2, column=0, padx=10, pady=10, sticky='e')
        self.traceCombobox = ttk.Combobox(self.widgetFrame, state='disabled', textvariable=self.traceVar)
        self.traceCombobox.grid(row=2, column=1, padx=10, pady=10, sticky='w')
        super().makeWidgets()

    def activateTraceField(self, *args):
        if self.plotNameVar.get():
            traces = []
            for line in self.master.controller.get_plots()[self.plotNameVar.get()].axes[0].lines :
                traces.append(line.get_label())
        self.traceCombobox.configure(state='readonly', values=traces)

    def okPressed(self, *args):
        for line in self.master.controller.get_plots()[self.plotNameVar.get()].axes[0].lines:
            if line.get_label() == self.traceVar.get():
                line.remove()
                break
        super().okPressed()
  
#==============================================================================================================================================
class ModifyTracePopup(GraphPopup):
    #popup that enables modification of a trace
    def __init__(self, master):
        super().__init__(master, "Modify Trace", plotNameVar=tk.StringVar(), traceVar=tk.StringVar(), colorVar=tk.StringVar(), linewidthVar=tk.StringVar())

    def activateOK(self, *args):
        if self.linewidthVar.get().isdecimal():
            super().activateOK(*args)

    def activateTraceField(self, *args):
        if self.plotNameVar.get():
            traces = []
            for line in self.master.controller.get_plots()[self.plotNameVar.get()].axes[0].lines :
                traces.append(line.get_label())
 
            self.traceCombobox.configure(state='readonly', values=traces)
        else:
            self.traceCombobox.configure(state='disabled', values=[])

    def traceVars(self):
        super().traceVars()
        self.plotNameVar.trace('w', self.activateTraceField)

    def makeWidgets(self):
        #plot label and combobox
        plotLabel = tk.Label(self.widgetFrame, text="Plot:")
        plotLabel.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        plotCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(self.master.controller.get_plots().keys()), textvariable=self.plotNameVar)
        plotCombobox.grid(row=0, column=1, padx=10, pady=10, sticky='w')
       
        #trace label and combobox
        traceLabel = tk.Label(self.widgetFrame, text="Trace:")
        traceLabel.grid(row=2, column=0, padx=10, pady=10, sticky='e')
        self.traceCombobox = ttk.Combobox(self.widgetFrame, state='disabled', textvariable=self.traceVar)
        self.traceCombobox.grid(row=2, column=1, padx=10, pady=10, sticky='w')

        #colour label and combobox
        colourLabel = tk.Label(self.widgetFrame, text="Colour:")
        colourLabel.grid(row=3, column=0, padx=10, pady=10, sticky='e')
        colourCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(mcolors.CSS4_COLORS), textvariable=self.colorVar)
        colourCombobox.grid(row=3, column=1, padx=10, pady=10, sticky='w')

        #linewidth label and entry
        linewidthLabel = tk.Label(self.widgetFrame, text="Line width:")
        linewidthLabel.grid(row=4, column=0, padx=10, pady=10, sticky='e')
        linewidthEntry = ttk.Entry(self.widgetFrame, textvariable=self.linewidthVar)
        linewidthEntry.grid(row=4, column=1, padx=10, pady=10, sticky='w')

        self.makeAlertBox()
        super().makeWidgets()

    def activateOK(self, *args):
        self.okButton.configure(state='disabled')
        if self.traceVar.get() and (self.colorVar.get() or self.linewidthVar.get().isdecimal()) :
            self.okButton.configure(state='normal')

    def okPressed(self, *args):
        try:
            for line in self.master.controller.get_plots()[self.plotNameVar.get()].axes[0].lines :
                if line.get_label() == self.traceVar.get():
                    if self.linewidthVar.get():
                        line.set_linewidth(float(self.linewidthVar.get()))
                    if self.colorVar.get():
                        line.set_color(self.colorVar.get())
                    break
            super().okPressed()
        except ValueError:
            self.alertBox.configure(text="Line width must be numeric.")

#==============================================================================================================================================
class ArithmeticPopup(ConditionalPopup):
    #popup that enables operations on spectra
    def __init__(self, master):
        self.functionClass = SpectrumOperations
        super().__init__(master, "Spectral Arithmetic", nameVar=tk.StringVar(),
                                                 opVar=tk.StringVar(),
                                                 s1Var=tk.StringVar())
        self.s2Var = None

    def traceVars(self):
        super().traceVars()
        self.opVar.trace('w', self.activateAuxiliaryField)

    def makeWidgets(self):
        nameLabel = tk.Label(self.widgetFrame, text="Name the result spectrum:")
        nameLabel.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        
        nameEntry = ttk.Entry(frame, textvariable=self.nameVar)
        nameEntry.grid(row=0, column=1, padx=10, pady=10, sticky='w')

        s1Label = tk.Label(self.widgetFrame, text="Spectrum 1:")
        s1Label.grid(row=1, column=0, padx=10, pady=10, sticky='e')
        
        s1Combobox = ttk.Combobox(frame, values=list(self.master.controller.get_spectra().keys()), state='readonly', textvariable=self.s1Var)
        s1Combobox.grid(row=1, column=1, padx=10, pady=10,sticky='w')

        opLabel = tk.Label(self.widgetFrame, text="Operation:")
        opLabel.grid(row=2, column=0, padx=10, pady=10, sticky='e')

        opCombobox = ttk.Combobox(frame, values=list(member[0] for member in inspect.getmembers(self.functionClass) if not member[0].startswith('__')), state='readonly', textvariable=self.opVar)
        opCombobox.grid(row=2, column=1, padx=10, pady=10, sticky='w')

        s2Label = tk.Label(self.widgetFrame, text="Spectrum 2:")
        s2Label.grid(row=3, column=0, padx=10, pady=10, sticky='e')

        self.s2Combobox = ttk.Combobox(self.widgetFrame, values=list(self.master.controller.get_spectra().keys()), state='disabled')
        self.s2Combobox.grid(row=3, column=1, padx=10, pady=10, sticky='w')

        self.makeAlertBox()
        super().makeWidgets()

    def activateAuxiliaryField(self, *args):
        self.s2Combobox.configure(state='disabled')
        if len(list(param for param in inspect.signature(getattr(self.functionClass, self.opVar.get())).parameters if param != 'self')) > 1:
            self.s2Var = tk.StringVar()
            self.s2Var.trace('w', self.activateOK)
            self.s2Combobox.configure(state='readonly', textvariable=self.s2Var)

    def okPressed(self, *args):
        try:
            if self.s2Var is not None:
                result = self.master.controller.operation(self.functionClass, self.opVar.get(), self.nameVar.get(), self.master.controller.get_spectra()[self.s1Var.get()], self.master.controller.get_spectra()[self.s2Var.get()])

            else:
                result = self.master.controller.operation(self.functionClass, self.opVar.get(), self.nameVar.get(), self.master.controller.get_spectra()[self.s1Var.get()])
            super().okPressed()

        except BadAxisSymmetryException as inst:
            self.alertBox.configure(text=inst.message)

#======================================================================================================================================================        
class GrindingCurvePopup(ConditionalPopup):
    #popup that enables creating a grinding curve
    def __init__(self, master):
        super().__init__(master, "Grinding Curve", nameVar=tk.StringVar(), mineralVar=tk.StringVar())
        self.spectra = []

    def makeWidgets(self):
        mineralLabel = tk.Label(self.widgetFrame, text="Mineral:")
        mineralLabel.grid(row=1, column=0, padx=10, pady=10, sticky='e')
        
        mineralCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=[mineral.name for mineral in Minerals], textvariable=self.mineralVar)
        mineralCombobox.grid(row=1, column=1, padx=10, pady=10, sticky='w')

        nameLabel = tk.Label(self.widgetFrame, text="Name the curve:")
        nameLabel.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        
        nameEntry = ttk.Entry(self.widgetFrame, textvariable=self.nameVar)
        nameEntry.grid(row=0, column=1, padx=10, pady=10, sticky='w')
        
        spectraLabel = tk.Label(self.widgetFrame, text="Spectra:")
        spectraLabel.grid(row=2, column=0, padx=10, pady=10, sticky='e')
        
        listboxFrame = tk.Frame(self.widgetFrame)
        listboxFrame.grid(row=2, column=1, padx=10, pady=10, sticky='w')

        yscrollbar = ttk.Scrollbar(listboxFrame)
        yscrollbar.grid(row=0, column=1, sticky='ns')
        
        self.spectraListbox = tk.Listbox(listboxFrame, selectmode='multiple', yscrollcommand=yscrollbar.set)
        self.spectraListbox.grid(row=0, column=0, sticky='nsew')
        self.fillListbox()
        self.spectraListbox.bind('<<ListboxSelect>>', self.activateOK)
        
        super().makeWidgets()

    def fillListbox(self):
        #populate the listbox with the spectra names
        for spectrumName in self.master.controller.get_spectra().keys():
            self.spectraListbox.insert('end', spectrumName)
        
    def activateOK(self, *args):
        for i in self.spectraListbox.curselection():
            self.spectra.append(self.master.controller.get_spectra()[self.spectraListbox.get(i)])
        if self.spectra:
           super().activateOK() 
        
    def okPressed(self, *args):
        for mineral in Minerals:
            if mineral.name == self.mineralVar.get():
                self.master.controller.operation(ParameterisedOperations, 'grinding_curve', self.nameVar.get(), mineral=mineral, *self.spectra)
                break
        super().okPressed()

#================================================================================================================================================================
class ZeroSpectrumPopup(ConditionalPopup):
    def __init__(self, master):
        super().__init__(master, "Zero Spectrum", spectrumVar=tk.StringVar(),
                                                     newNameVar=tk.StringVar(),
                                                     leftIndexVar=tk.StringVar(),
                                                     rightIndexVar=tk.StringVar())

    def makeWidgets(self):
        spectraLabel = tk.Label(self.widgetFrame, text="Spectrum:")
        spectraLabel.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        spectraCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(self.master.controller.get_spectra().keys()), textvariable=self.spectrumVar)
        spectraCombobox.grid(row=0, column=1, padx=10, pady=10, sticky='w')

        nameLabel = tk.Label(self.widgetFrame, text="Name the result spectrum:")
        nameLabel.grid(row=1, column=0, padx=10, pady=10, stick='e')
        nameEntry = ttk.Entry(self.widgetFrame, textvariable=self.newNameVar)
        nameEntry.grid(row=1, column=1, padx=10, pady=10, sticky='w')

        indicesLabel = tk.Label(self.widgetFrame, text="Indices:")
        indicesLabel.grid(row=2, column=0, padx=10, pady=10, sticky='e')
        
        indicesFrame = tk.Frame(self.widgetFrame)
        indicesFrame.grid(row=2, column=1, pady=10, sticky='w')

        leftIndexEntry = ttk.Entry(indicesFrame, textvariable=self.leftIndexVar)
        leftIndexEntry.grid(row=0, column=0, padx=5, sticky='e')
        
        rightIndexEntry = ttk.Entry(indicesFrame, textvariable=self.rightIndexVar)
        rightIndexEntry.grid(row=0, column=1, padx=5, sticky='w')
        
        super().makeWidgets()

    def activateOK(self, *args):
        self.okButton.configure(state='disabled')
        if self.spectrumVar.get() and self.leftIndexVar.get().isnumeric() and self.rightIndexVar.get().isnumeric():
            self.okButton.configure(state='normal')

    def okPressed(self, *args):
        if not self.newNameVar.get().strip():
            self.newNameVar.set(self.spectrumVar.get())
        self.master.controller.operation(ParameterisedOperations, 'zero', self.newNameVar.get(), self.master.controller.get_spectra()[self.spectrumVar.get()], leftidx=int(self.leftIndexVar.get()), rightidx=int(self.rightIndexVar.get()))
        super().okPressed()

#==========================================================================================================================================================================================================================================================================
class NewPlotPopup(ConditionalPopup):
    #popup that enables creation of a new plot
    def __init__(self, master):
        super().__init__(master, "Make new plot", plotNameVar=tk.StringVar())

    def makeWidgets(self):
        plotLabel = tk.Label(self.widgetFrame, text="Name the new plot:")
        plotLabel.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        
        plotEntry = ttk.Entry(self.widgetFrame, textvariable=self.plotNameVar)
        plotEntry.grid(row=0, column=1, padx=10, pady=10, sticky='w')

        super().makeWidgets()

    def okPressed(self, *args):
        self.master.controller.make_plot(self.plotNameVar.get())
        self.master.showFigure(self.master.controller.get_plots()[self.plotNameVar.get()])
        super().okPressed()

#======================================================================================================================================================
class DeletePlotPopup(GraphPopup):
    #popup that enables deletion of an existing plot
    def __init__(self, master):
        super().__init__(master, "Delete Plot", plotNameVar=tk.StringVar())

    def makeWidgets(self):
        plotLabel = tk.Label(self.widgetFrame, text="Plot to delete")
        plotLabel.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        
        plotCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(self.master.controller.get_plots().keys()), textvariable=self.plotNameVar)
        plotCombobox.grid(row=0, column=1, padx=10, pady=10, sticky='w')
        
        super().makeWidgets()

    def okPressed(self, *args):
        self.master.controller.delete_plot(self.plotNameVar.get())
        self.master.canvas.get_tk_widget().delete('all')

        if len(self.master.controller.get_plots()) >=1:
            self.master.showFigure(list(self.master.controller.get_plots().values())[0])
        super().okPressed()
        
#==============================================================================================================================================
class ShowPlotPopup(GraphPopup):
    #popup that allows the user to toggle display of a plot
    def __init__(self, master):
        super().__init__(master, "Show plot", plotNameVar = tk.StringVar())

    def makeWidgets(self):
        nameLabel = tk.Label(self.widgetFrame, text="Show plot:")
        nameLabel.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        
        plotCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(self.master.controller.get_plots().keys()), textvariable=self.plotNameVar)        
        plotCombobox.grid(row=0, column=1, padx=10, pady=10, sticky='w')

        super().makeWidgets()

    def okPressed(self, *args):
        self.master.showFigure(self.master.controller.get_plots()[self.plotNameVar.get()])
        super().okPressed()

#==============================================================================================================================================
class ModifyPlotPopup(GraphPopup):
    #popup that allows the user to modify the appearance of a plot
    def __init__(self, master):
        super().__init__(master, "Modify Plot", plotVar=tk.StringVar(),
                                                 titleVar=tk.StringVar(),
                                                 xVar=tk.StringVar(),
                                                 yVar=tk.StringVar(),
                                                 lxlimVar=tk.StringVar(),
                                                 rxlimVar=tk.StringVar(),
                                                 lylimVar=tk.StringVar(),
                                                 rylimVar=tk.StringVar(),
                                                 legendVar=tk.BooleanVar())

    def makeWidgets(self):
        plotLabel = tk.Label(self.widgetFrame, text="Plot:")
        plotLabel.grid(row=0, column=0, padx=10, pady=10, sticky='e')
        plotCombobox = ttk.Combobox(self.widgetFrame, state='readonly', values=list(self.master.controller.get_plots().keys()), textvariable=self.plotVar)
        plotCombobox.grid(row=0, column=1, padx=10, pady=10, sticky='w')
        
        titleLabel = tk.Label(self.widgetFrame, text="Rename:")
        titleLabel.grid(row=2, column=0, padx=10, pady=10, sticky='e')
        titleEntry = ttk.Entry(self.widgetFrame, textvariable=self.titleVar)
        titleEntry.grid(row=2, column=1, padx=10, pady=10, sticky='w')

        xLabel = tk.Label(self.widgetFrame, text="x Label:")
        xLabel.grid(row=3, column=0, padx=10, pady=10, sticky='e')
        xEntry = ttk.Entry(self.widgetFrame, textvariable=self.xVar)
        xEntry.grid(row=3, column=1, padx=10, pady=10, sticky='w')

        yLabel = tk.Label(self.widgetFrame, text="y Label:")
        yLabel.grid(row=4, column=0, padx=10, pady=10, sticky='e')
        yEntry = ttk.Entry(self.widgetFrame, textvariable=self.yVar)
        yEntry.grid(row=4, column=1, padx=10, pady=10, sticky='w')

        legendLabel = tk.Label(self.widgetFrame, text="Show legend?")
        legendLabel.grid(row=6, column=0, padx=10, pady=10, sticky='e')
        legendCheckbutton = ttk.Checkbutton(self.widgetFrame, variable=self.legendVar)
        legendCheckbutton.grid(row=6, column=1, padx=10, pady=10, sticky='w')

        limitsContainer = tk.Frame(self.widgetFrame)
        limitsContainer.grid(row=5, column=0, columnspan=2, padx=10)

        xlimLabel = tk.Label(limitsContainer, text="x Limits")
        xlimLabel.grid(row=0, column=0, pady=5, sticky='w')
        
        lxlimEntry = ttk.Entry(limitsContainer, textvariable=self.lxlimVar)
        lxlimEntry.grid(row=1, column=0, padx=5, sticky='e')
        
        rxlimEntry = ttk.Entry(limitsContainer, textvariable=self.rxlimVar)
        rxlimEntry.grid(row=1, column=1, padx=5, sticky='w')

        ylimLabel = tk.Label(limitsContainer, text="y Limits")
        ylimLabel.grid(row=0, column=2, pady=5, sticky='w')
        
        lylimEntry = ttk.Entry(limitsContainer, textvariable=self.lylimVar)
        lylimEntry.grid(row=1, column=2, padx=5, sticky='e')

        rylimEntry = ttk.Entry(limitsContainer, textvariable=self.rylimVar)
        rylimEntry.grid(row=1, column=3, padx=5, sticky='w')
        
        super().makeWidgets()

    def activateOK(self, *args):
        if self.plotVar.get():
            self.okButton.configure(state='normal')
        else:
            self.okButton.configure(state='disabled')

    def okPressed(self, *args):
        if self.xVar.get():
            self.master.controller.get_plots()[self.plotVar.get()].axes[0].set_xlabel(self.xVar.get())
        if self.yVar.get():
            self.master.controller.get_plots()[self.plotVar.get()].axes[0].set_ylabel(self.yVar.get())            
        if self.legendVar.get():
            self.master.controller.get_plots()[self.plotVar.get()].axes[0].legend()
        if not self.legendVar.get():
            self.master.controller.get_plots()[self.plotVar.get()].axes[0].legend().remove()

        if all(entry.get().isnumeric() for entry in {self.lxlimEntry, self.rxlimEntry}):
            self.master.controller.get_plots()[self.plotVar.get()].axes[0].set_xlim(float(self.lxlimEntry.get()), float(self.rxlimEntry.get()))

        if all(entry.get().isnumeric() for entry in {self.lylimEntry, self.rylimEntry}):
            self.master.controller.get_plots()[self.plotVar.get()].axes[0].set_ylim(float(self.lylimEntry.get()), float(self.rylimEntry.get()))

        if self.titleVar.get():
            self.master.controller.get_plots()[self.plotVar.get()].suptitle(self.titleVar.get())
            self.master.controller.rename_plot(self.plotVar.get(), self.titleVar.get())

        super().okPressed()
#==============================================================================================================================================
class UnsupportedFileTypeException(Exception):
    def __init__(self, path):
        self.path=path #the filepath of the file that caused the exception
        self.message = "The file type of " + self.path + "\nis not supported at this time."

#==============================================================================================================================================
class NoPathNameException(Exception):
    def __init__(self, fnf_inst):
        self.filename = fnf_inst.filename
        if str(self.filename) == "b''":
            self.message = "The Open File window was closed before a file was chosen"
        else:
            self.message = "File " + self.filename + " could not be found."

#==============================================================================================================================================
class BadAxisSymmetryException(Exception):
    def __init__(self):
        self.message = " The x-axes are incongruent."

#==============================================================================================================================================      
'''--------------------------------------------------------------------------------------------------------------------------------------------'''
def main():
    App().mainloop()
    
    
main()
'''--------------------------------------------------------------------------------------------------------------------------------------------'''
