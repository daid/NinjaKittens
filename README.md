NinjaKittens
============
2.5D CNC GCode generation tool based on Cura. In Alpha. 

Features: 
- Supports dxf and svg files
- Change settings per shape (also inside a file)
- Direct drill path preview
- Cross platform (wxPython)
- Ajusts for drill width
- Tabs
- Export to Trotec laser file 
ToDo:
- Engrave (remove whole area instead of the contours)

Build: 
```
cd Engine
make
cd ../
export PYTHONPATH=.
python NK/nk.py
```

Dependencies:
- python2.7
- py-wxpython-2.8
- py-opengl
