from pymongo import MongoClient
from bson.objectid import ObjectId
import networkx as nx
import shapefile
from fa2 import ForceAtlas2
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure
import urllib.request

#for converting type to type to display on frontend
type_formatter = {'payment': 'paid', 'charge' : 'charged'}

#configure mongodb client
client = MongoClient()
db = client.test
venmo = db.venmo

mongo_transactions = venmo.find({'payment.target.user.display_name':'Heather Hughes'})#.limit(1)#'actor':{'display_name': 'Jillian Boose'}
print(mongo_transactions)
for item in mongo_transactions:

    print(item)
#configure forceAtlas2 simulation (Fruchterman Reingold spring simulation with Barnes Hut approximation)
forceatlas_instance = ForceAtlas2(
                        # Behavior alternatives
                        outboundAttractionDistribution=True,  # Dissuade hubs
                        linLogMode=False,  # NOT IMPLEMENTED
                        adjustSizes=False,  # Prevent overlap (NOT IMPLEMENTED)
                        edgeWeightInfluence=1.0,

                        # Performance
                        jitterTolerance=1.0,  # Tolerance
                        barnesHutOptimize=True,
                        barnesHutTheta=2,
                        multiThreaded=False,  # NOT IMPLEMENTED

                        # Tuning 0.000025 for 1m nodes
                        scalingRatio=0.000025,
                        strongGravityMode=False,
                        gravity=0.8,

                        # Log
                        verbose=True)




def runSimulation(mongo_transactions, forceatlas_instance):
    g = nx.Graph()
    print("adding nodes and edges to graph")
    addGraphContents(g, mongo_transactions)

    print("starting simulation...")
    positions = forceatlas_instance.forceatlas2_networkx_layout(g, pos=None, iterations=100)

    print("drawing Graph")
    draw_graph(g, positions)

    print("saving nodes")
    exportNodesSHP(g, positions)

    print("saving node projection")
    writePRJ("./shapefiles/test/test_nodes2")

    print("saving edges")
    exportEdgesSHP(g, positions)

    print("saving edge projection")
    writePRJ("./shapefiles/test/test_edges2")

    print("done!")


#formatting the transaction record for slightly easier usage.
#  => might modify database later to eliminate this step
def unpackTransaction(transac):
    result = {}
    result['actor_id'], result['target_id'] = transac['payment']['actor']['id'], transac['payment']['target']['user']['id']
    result['actor_username'], result['target_username'] = transac['payment']['actor']['username'], transac['payment']['target']['user']['username']
    result['actor_name'], result['target_name'] = transac['payment']['actor']['display_name'], transac['payment']['target']['user']['display_name']
    result['message'] = transac['note']
    result['transac_date'] = transac['date_created']
    result['action'] = type_formatter[transac['type']]

    return result

def addGraphContents(g, mongo_transactions):
    count_invalid = 0
    for transac in mongo_transactions:
        if not transac['payment'] or not transac['payment']['target'] or not transac['payment']['target']['user']:
            count_invalid += 1
            continue

        unpacked = unpackTransaction(transac)
        g.add_node(unpacked['actor_id'], username=unpacked['actor_username'])
        g.add_node(unpacked['target_id'], username=unpacked['target_username'])

        g.add_edge(unpacked['target_id'], unpacked['actor_id'], attrib=
            {'target_name': unpacked['target_name'],
            'actor_name': unpacked['actor_name'],
            'target_username': unpacked['target_username'],
            'actor_username': unpacked['actor_username'],
            'date': unpacked['transac_date'],
            'action': unpacked['action'],
            'message': unpacked['message']})



    print("there are ", count_invalid, " transactions that can't be graphed")



def exportEdgesSHP(g, positions):
    w_edges = shapefile.Writer('./shapefiles/test/test_edges2')
    w_edges.shapeType = 3
    w_edges.field('name', 'C', '20')
    w_edges.field('target_name', 'C', '25')
    w_edges.field('actor_name', 'C', '25')
    w_edges.field('date', 'C', '22')
    w_edges.field('action', 'C', '8')
    w_edges.field('message', 'C') #encoding might be weird here...

    counter2 = 0
    for node1, node2, attrib in g.edges(data='attrib'):
        start_pt, end_pt = list(positions[node1]), list(positions[node2])
        start_pt[0] = start_pt[0] * 1.57
        start_pt[1] = start_pt[1] * 0.80
        end_pt[0] = end_pt[0] * 1.57
        end_pt[1] = end_pt[1] * 0.80
        w_edges.line([[start_pt, end_pt]])
        w_edges.record(str(counter2), attrib['target_name'],
            attrib['actor_name'],
            attrib['date'],
            attrib['action'],
            attrib['message'] ) # dict unpacking doesn't seem to be supported here (?)
        counter2 += 1
    print(counter2)
    w_edges.close()


# function to generate .prj file information using spatialreference.org
def getWKT_PRJ (epsg_code):
     import urllib
     # access projection information
     with urllib.request.urlopen("http://spatialreference.org/ref/epsg/{0}/prettywkt/".format(epsg_code)) as wkt:
     # remove spaces between charachters
        remove_spaces = wkt.read().decode('utf-8').replace(" ","")
        # place all the text on one line
        output = remove_spaces.replace("\n", "")
        return output


def writePRJ(name):
# create the .prj file
    prj = open(f'{name}.prj', "w")
    # will always use use epsg 4326
    epsg = getWKT_PRJ("4326")
    prj.write(epsg)
    prj.close()


def exportNodesSHP(g, positions):
    w_nodes = shapefile.Writer('./shapefiles/test/test_nodes2')
    w_nodes.shapeType = 1
    w_nodes.field('name', 'C', '20')
    w_nodes.field('username', 'C', '30')
    w_nodes.field('degree', 'N')

    for node_key in positions:
        x,y = positions[node_key]
        x2 = x * 1.57
        y2 = y * 0.80
        w_nodes.point(x2, y2)
        w_nodes.record(str(node_key), g.nodes[node_key]['username'], g.degree[node_key]) # write node name, node degree. node degree used for styling

    w_nodes.close()

def draw_graph(g, positions):
    nx.draw_networkx_nodes(g, positions, node_size=20, with_labels=False, node_color="blue", alpha=0.4)
    nx.draw_networkx_edges(g, positions, edge_color="green", alpha=0.5)
    plt.axis('off')
    plt.savefig('shapefile_graph.png')


runSimulation(mongo_transactions, forceatlas_instance)

#for convering geojson utf-8 invalid to geojson utf-8 valid
#iconv -f UTF-8 -t UTF-8//IGNORE -o mod_1m.geojson 1m_edges.geojson...  


#for generating mbtiles use the following in tippecanoe
#-j '{ "*": ["all", [ "attribute-filter", "actor_name", [ ">=", "$zoom", 6 ] ], [ "attribute-filter", "target_name", [">=","$zoom", 6]], [ "attribute-filter", "date", [">=","$zoom", 6]], [ "attribute-filter", "action", [">=","$zoom", 6]], [ "attribute-filter", "message", [">=","$zoom", 6]] ] }'


#for generating the nodes use the following in tippecanoe
#-j '{ "*": ["all", [ "attribute-filter", "username", [ ">=", "$zoom", 7 ] ], [ "attribute-filter", "degree", [">=","$zoom", 7]] ] }'
