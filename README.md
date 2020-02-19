# VenmoViz
This README walks you through the process of creating your own large, navigateable social network graph.
[The finished project](http://venmoviz.appspot.com/) consists of ~1.6 million nodes and ~1 million edges, using about one-eighth the total data set. The graph is navigateable as if it was Google Maps or Open Street Maps, and displays transaction and user data. 

## Necessary Tools
- MongoDB (depending on data set)
- Python3
- [Python Force Atlas 2](https://github.com/bhargavchippada/forceatlas2) (FA2) for running graph force-layout algorithm
- [ogr2ogr CLI](https://gdal.org/programs/ogr2ogr.html) for converting geospacial file formats
- [ICONV CLI](https://www.gnu.org/savannah-checkouts/gnu/libiconv/documentation/libiconv-1.15/iconv.1.html) for converting file encodings
- [tippecanoe CLI](https://github.com/mapbox/tippecanoe) for generating vector MBtiles to serve, that Mapbox will allow


## Background Info
If you are completely new to geographical data, the sections below might be a bit overloaded with needlessly complicated, but convenient terms. This section tries to clear that up.

#### What is a Shapefile?
A Shapefile is actually a set of three or more files, typically four (.shp, .dbf, .prj, .shx ). The .shp file contains coordinate data, as well as the type of geometry at that coordinate. These geometries are often called 'features'. Each .shp file is also constrained to one type of geometry (point, line, polygon). The .shx file is a machine code version of the .shp file, for fast processing. The .dbf file is the file that contains additional attributes to the features. For example, if I wanted to add a description to the features in the .shp file, I would store that description in the .dbf file under a unique key. The .prj file is one of a few optional files that simply defines the type of geometric projection that the points use, or how the coordinates should be mapped to latitude and longitude. For this project I use [EPSG:4326](https://epsg.io/4326), also known as WGS 84.

#### What is a Force Directed Layout?
If we were to just plop all of our graph points randomly on a coordinate system, the graph would look very chaotic and not be very readable. A force directed layout algorithm simulates the edges between the nodes as springs over a number of iterations. This causes the graph to settle into an equilibrium where connected nodes are positioned much closer to each other. Typically, as with NetworkX's graph layout algorithm, this runs in O(n<sup>2</sup>), which runs very slow for more than about 100,000 edges and nodes. However, Force Atlas 2 implements the [Barnes-Hut optimization](https://en.wikipedia.org/wiki/Barnes%E2%80%93Hut_simulation) yielding a runtime of O(nlog(n)). On an i5-8250U laptop CPU with 8GB of RAM it takes about 45 minutes to simulate 1 million edges and 1.6 million nodes over 100 iterations *with* the optimization.

#### What are MBtiles?
MBtiles are used to efficiently serve geospatial data. Tiles are squares of vector or raster data that get loaded discretely--usually 256x256 pixels in size. They can be customized to show certain data on certain zoom levels to enhance load speed and responsiveness. Put simply, it is a SQLite database that can query efficiently on coordinates or sections.

## Data
And, of course you should have a data set you want to transform into a graph. I used a large set of [Venmo transactions](https://github.com/sa7mon/venmo-data), although you can use any data set that you can transform into a graph. The linked Venmo data will have to be interfaced with MongoDB.

## Methods
The general workflow for the graph creation process is as follows:
query data, parse it, and run an optimized force-layout algorithm on the nodes (Barnes-Hut Force Atlas 2). Save this data in a shapefile, then convert the shapefile to a GeoJSON (JSON specification for geodata) file with ogr2ogr CLI. If the output of ogr2ogr is, for some reason, corrupted then iconv can repair the file. Use Tippecanoe CLI to convert the repaired GeoJSON to MBtiles format. Finally, you either host the tiles yourself and enjoy restriction-free tiles, or tweak the tippecanoe commands until your MBtiles are compressed enough to upload to Mapbox for hosting. Once hosted, it is just some straightforward javascript using [Mapbox GL JS ](https://docs.mapbox.com/mapbox-gl-js/api/) to get everything looking pretty.

Now with the big picture in mind, a bit more detail.

#### Data Processing
First I trimmed the Venmo data set down considerably. I used the function call in [update_query](https://github.com/karoster/venmo_viz/blob/master/graph_creation/update_query.json) to cut the amount of raw data in half.
Next I ran the processing in [venmo_data.py](https://github.com/karoster/venmo_viz/blob/master/graph_creation/venmo_data.py).
The data processing was only a matter of adding the graph nodes/edges to a networkx graph with their respective attributes, then running the Force Layout algorithm to get the final node positions. Networkx was handy in the way it allowed me to store data under the node's key and automatically tracked node degree for later styling purposes. I then used [pyshp](https://pypi.org/project/pyshp/) to create the shapefiles with the node and edge positions/attribute data.

Optionally, here one could load the data into [Tilemill](https://tilemill-project.github.io/tilemill/docs/crashcourse/introduction/) to check and see what the data looks like. This is helpful to make sure the data has the right spacing, and is properly formatted before taking the time to upload it to Mapbox (for instance, Mapbox won't let you upload data if any of the points are outside of a [180, 180] Lat./Lon. range). I would avoid rendering MBtiles with TileMill as these are *raster* tiles and won't be nearly as high of quality as vector tiles. The style sheets that I made on Tilemill that my hosted example are based off of can be found [here](https://github.com/karoster/venmo_viz/tree/master/graph_creation/tilemill_styles).


#### File Conversion
You might be wondering: why don't you just upload the shapefiles to Mapbox directly? There is simply too much data! We need to be able to filter the data with Tippecanoe before uploading. Mapbox doesn't allow you to have any single tile with more than 0.5 MB worth of data, and each of our now generated shapefiles are ~0.5 GB. That means--at zoom level 0, where the entire map is only broken into about twelve 256x256 pixel tiles (or less)--you far exceed this limit. So, foreshadowing a bit, file conversion will allow us to trim our data to various appropriate zoom levels. 

What we have currently are two shapefiles: one for edges, and one for nodes. Tippecanoe takes GeoJSON, so we need to convert these to GeoJSON with the industry standard for geospatial file conversion: ogr2ogr. 
The command will look something like this in terminal (note I had trouble getting ogr2ogr to interact well with a Debian WSL distro, if anyone is using that).

```
ogr2ogr -f GeoJSON output.geojson input.shp
```

So now what we are left with is two GeoJSON files. **In the next step you may run into the error** 'could not read extended-ascii non-unicode at position XXX' or something similar when generating the MBtiles. This entirely depends on your dataset! If you do run into this problem, and you believe your file to be correctly encoded in utf-8 (can view emojis in VSCode), as it should be because Python works in utf-8 and geojson are standard utf-x, iconv might be a quick fix.
I fixed that error with the following command:

```
#iconv -f UTF-8 -t UTF-8//IGNORE -o output.geojson input.geojson  

```

the //IGNORE flag just ignores invalid utf-8 characters if they can't be converted. This can be a quick-fix for bad formatted utf-8.
Great! we now have two properly formatted GeoJSON files with all of our geometry data.

#### MBtile Generation
As mentioned earlier it is necessary to indepenently generate MBtiles if you are working with larger data sets, due to constraints put in place by Mapbox. This step is mostly a guess and check on what looks good on what zoom levels. I **highly** recommend reading the [tippecanoe docs](https://github.com/mapbox/tippecanoe) to see the surprisingly versatile methods available. I realized when generating my tiles that there are too many nodes to view edges until zoom ~5 (again, I used Tilemill to get a preview of what things would look like). So I limited my edges to only start on zoom = 5. Along with this, I limit the data that the tiles query for until zoom = 6. Infact I grab *no* data until zoom = 6. This is the filter I used while generating edge tiles (tippecanoe docs are helpful here...).
```
-j '{ "*": ["all", [ "attribute-filter", "actor_name", [ ">=", "$zoom", 6 ] ], [ "attribute-filter", "target_name", [">=","$zoom", 6]], [ "attribute-filter", "date", [">=","$zoom", 6]], [ "attribute-filter", "action", [">=","$zoom", 6]], [ "attribute-filter", "message", [">=","$zoom", 6]] ] }'
```

Similarly I did the same for nodes at zoom = 7. However, I started generating nodes at zoom = 3. degree must remain present at all times as that is what determines the style of the nodes (higher degree -> bigger nodes, different color) at a later step.

```
-j '{ "*": ["all", [ "attribute-filter", "username", [ ">=", "$zoom", 7 ] ], [ "attribute-filter", "degree", [">=","$zoom", 3]] ] }'
```

I then uploaded these tilesets to Mapbox for styling and hosting. If you run into a 'tile too large' error during upload, you might need to constrain the tiles more. If you plan on hosting your own tiles, you can remove tippecanoe's max-tile-size parameter when generating the tiles; which is very helpful but will increase render time when serving the tiles to clients.


#### Styling
I styled the tiles in Mapbox studio. I used my previous Tilemill stylesheets as a guide and did a lot of googling. There is not a whole lot to say here other as the Mapbox studio UI is fairly comprehensive. You can add styles and event listeners on clientside after the vector tile data gets served.

#### Hosting
I hosted VenmoViz on Flask and Google App Engine, using Mapbox GL JS to make requests to Mapbox for me and add interactivity to my graph map. You can see that javascript [here](https://github.com/karoster/venmo_viz/blob/master/graph_host/static/javascript/map_listeners.js).


[Thanks for reading](http://venmoviz.appspot.com)!
