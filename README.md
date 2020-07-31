# **Spectacular** #

## v.0.6.1 ##

 A desktop app for viewing and manipulating FTIR Spectra developed for the Poduska Research Group, Memorial University.

---
 ## **Contributors** ##
 ---
 Cassandra Clowe-Coish <github.com/fortunetellingfish>  

---
 ## **Implementation Details** ##
 ---
 + ### Tkinter  Graphical User Interface ###
+ ### Pandas Data Backend ###
+ ### Matplotlib Plotting Backend ###

---
## **App Features** ##
---
* ## General ##
    The app pages all have a "Navigation Tray" on the left hand side to navigate to other pages. There is a "Widget Frame" as the main applcation window, containing widgets specific to that page, and a small alert box at the bottom of the page, below the widget frame, to alert the user of errors and... well, alerts.  
    Most buttons on the app pages trigger toplevel popups to perform operations.

    + ### Home Page ###
        The landing pahe of the application. 
        From this page,the user can load delimited & fixed width files.
        + #### Roadmap ####
          More file type compatibility.

    + ### Tutorial Page  (**in development**) ###
        A page, similar to this README, intended to outline the usage specifications of the application, but with fewer "under the hood" details. The only widget so far is a text box.  
        + #### Roadmap ####
            Write external md files detailing usage of each app page and import them into the text box, and implement tutorial page navigation buttons, to "turn the pages" of the tutorial.
    + ### Make Spectrum Page ###
        From this page, data loaded from a file is used to instantiate a Spectrum object. The user must choose a source file, and select which column will denote the x axis and which will denote the y axis. The user must also provide a name for the Spectrum object.  
        When the user selects a source fikle from the drop-down list, the data will appear in the preview box on the right-hand side of the widget frame.

    + ### Spectra Page ###
      From this page, the user can:  
      + View files and  the `df ` attribute of the Spectrum object represented as a string in the textbox on the right hand side of the page. Select either from its respective drop-down list. The name of the object will appear in a label above the text box.

      + Save the DataFrame of a Spectrum object as a csv file, using the "Save Spectrum" button.
    
      + Duplicate the data of an existing Spectrum object as a new Spectrum object with a different name. Useful for experimenting with data processing without changing the original object

      + Perform arithmetic operations on spectrum objects. Specifically, the `y` attributes of the objects comprise the operands, and the resultant spectrum object will have the same `x` attribute as the first operand. An operation will only be performed if both operands have the *identical* `x` attributes. Operations include `add`, `subtract`, `multiply`, and `divide`.

      + 


    + ### Graph Page ###
