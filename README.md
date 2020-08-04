# **Spectacular** #

## v.0.6.1 ##

 &nbsp; A desktop app for viewing and manipulating FTIR Spectra developed for the Poduska Research Group, Memorial University.

---
 ## **Contributors** ##
 ---
 Cassandra Clowe-Coish <github.com/fortunetellingfish>  

---
 ## **Implementation Specifications** ##
 ---
 + Tkinter  Graphical User Interface
+ Pandas Data Backend
+ Matplotlib Plotting Backend
+ Dynamic object storage in dictionaries.

---
## **App Features** ##
---
* ## General ##
    &nbsp; The app pages all have a "Navigation Tray" on the left hand side to navigate to other pages. There is a "Widget Frame" as the main applcation window, containing widgets specific to that page, and a small alert box at the bottom of the page, below the widget frame, to alert the user of errors and... well, alerts.  
   &nbsp;  Most buttons on the app pages trigger toplevel popups to perform operations.  
    In operations where a new object is created, such as a Spectrum or a Figure, existing objects will be "overwritten" if an object with the same name is already stored in the current App instance. This is because the objects are stored in dictionary attributes of the App instance.

    + ### Home Page ###
        &nbsp; The landing page of the application. 
        From this page,the user can load delimited & fixed width files.
        + #### Roadmap ####
          More file type compatibility.

    + ### Tutorial Page  (**in development**) ###
        &nbsp; A page, similar to this README, intended to outline the usage specifications of the application, but with fewer "under the hood" details. The only widget so far is a text box.  
        + #### Roadmap ####
            Write external md files detailing usage of each app page and import them into the text box, and implement tutorial page navigation buttons, to "turn the pages" of the tutorial.
    + ### Make Spectrum Page ###
         &nbsp; From this page, data loaded from a file is used to instantiate a Spectrum object. The user must choose a source file, and select which column will denote the x axis and which will denote the y axis. The user must also provide a name for the Spectrum object.  
         &nbsp; When the user selects a source fikle from the drop-down list, the data will appear in the preview box on the right-hand side of the widget frame.

    + ### Spectra Page ###
      &nbsp; From this page, the user can:  
      + View files and  the `df ` attribute of the Spectrum object represented as a string in the textbox on the right hand side of the page. Select either from its respective drop-down list. The name of the object will appear in a label above the text box.

      + __Save Spectrum:__ Save the DataFrame of a Spectrum object as a csv file, using the "Save Spectrum" button.
    
      + __Delete Spectrum:__ Delete a spectrum object.

      + __Duplicate Spectrum:__ Duplicate the data of an existing Spectrum object as a new Spectrum object with a different name. Useful for experimenting with data processing without changing the original object

      + __Arithmetic:__ Perform arithmetic operations on spectrum objects. Specifically, the `y` attributes of the objects comprise the operands, and the resultant spectrum object will have the same `x` attribute as the first operand. An operation will only be performed if both operands have the *identical* `x` attributes. Operations include `add`, `subtract`, `multiply`, and `divide`.

      + __Grinding Curve:__ Create a grinding curve as a Spectrum object. This curve is a representation of how sample grinding affects peak size snd shape.

      + __Zero Spectrum:__ Make the y values of a Spectrum between two point indices equal zero. The source Spectrum can either be mutated directly by entering the same name in the name field, or a new object can be created by entering a different name.

    + ### Graph Page ###
        This is the page where the user can plot Spectrum objects and customise plots. One plot is displayed at a time, in the centre of the page. From the tray on the right, one can modify her plots.

         + __Add Trace:__ Creates a popup to add a line to the axis, with the df of a Spectrum object as the source. The trace must also be initialised with linewidth and colour parameters, which can be modified later.

         + __Delete Trace:__ Creates a popup to remove an existing trace from a plot.

         + __Modify Trace:__ Creates a popup to change the line width or the colour of a trace. Only one of these fields needs to be filled in order to activate the "OK" button. However, the "Plot" and "Trace" fields *must* be filled.

         + __New Plot:__ Creates a popup to make a new, single-axis plot. The new plot must be named.  

         + __Delete Plot:__
         Creates a popup to delete an existing Figure object.

         + __Modify Plot:__ Creates a popup to change aspects of the plot itself, such as the title, the x and y limits, the x and y limits, and to toggle the legend.

         + __Show Plot:__ Creates a popup to select which plot is displayed on the graph page.

         + __Update Legend:__ Refreshes the legend on the current plot. This button is necessary due to a known [bug][] in matplotlib, where the legend representtion of the lines on an axis do not change with the lines themselves.
         
         [bug]: https://github.com/matplotlib/matplotlib/issues/2035  
          
        &nbsp;
         + #### Roadmap ####
           Allow for multiple axes on the same plot.
