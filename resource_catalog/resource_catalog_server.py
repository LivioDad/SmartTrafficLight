import cherrypy
import json
import time

#every 10 seconds periodically registers in the service_catalog_server
class TLCatalogManager(object):
    exposed = True #cherrypy exposes class methods as endpoints REST

    '''
    handles HTTP requests to register resources, getting info of the broker
    and retrieve data related to devices
    catalog.json is the key because tracks devices and handles their info 
    and also updates the system thanks to the methods of TLCatalogManager
    '''

    def __init__(self, resource_catalog_info):
        self.catalog_file = 'catalog.json' #local archive for the info of the registerd devices and the broker
        self.catalog = json.load(open(self.catalog_file))
        self.resource_cat_info_file = resource_catalog_info
        self.resource_cat_info = json.load(open(self.resource_cat_info_file))
        #info to configure and comunicate of the resource_catalog


    def GET(self, *uri, **params):
        '''
        when a client does a GET the server reads the data in resoucesList (in catalog.json) to answer the request
        '''
        if len(uri[0]) > 0:
            if (uri[0] != 'broker') and (uri[0] != 'allResources') and (uri[0] != 'resourceID'):
                error_string = "incorrect URI:\n" + str(uri)
                raise cherrypy.HTTPError(400, error_string)
            else:
                if uri[0] == 'broker':
                    # Retrieve information about broker
                    brokerInfo = self.catalog['broker']
                    return json.dumps(brokerInfo)

                if uri[0] == 'allResources':
                    # Retrieve all registered devices
                    output = json.dumps(self.catalog['resourcesList'])
                    return output

                if uri[0] == 'resourceID':
                    # Retrieve the information of a device given its ID
                    id = int(params['ID'])
                    for item in self.catalog['resourcesList']:
                        if id == int(item['ID']):
                            output = json.dumps(item)
                            return output
                    return 'Resource/Device ID not found'



    #PUT used to register resouces in the service, receives a json message with the resource info
    def PUT(self, *uri, **params):
        if uri[0] == 'registerResource': #endpoint to register od update the resource
            body = cherrypy.request.body.read()
            json_body = json.loads(body)
            # Update "lastUpdate" of the resource
            json_body["lastUpdate"] = time.time() #also update last update time
            id = json_body['ID'] #iD of the resource
            try:
                for item in self.catalog['resourcesList']:  #for all registered resources in the catalog.json
                    if id == item['ID']: #look for the one with the same ID, if there is (so the resources its already registered)
                        #then just UPDATE its info
                        devicesList = self.catalog['resourcesList']
                        devicesList.remove(item) #remove the old version
                        devicesList.append(json_body) #append the new version
                        self.catalog['resourcesList'] = devicesList
                        # Update "lastUpdate" of resource catalog catalog.json
                        self.catalog['lastUpdate'] = time.time()
                        catalog_file = open(self.catalog_file, "w")
                        json.dump(self.catalog, catalog_file) #dump the updated catalog
                        return 'Registered successfully'

                #if the resources has not been found in the catalog then add it, REGISTRATION
                self.catalog['resourcesList'].append(json_body)
                # Update "lastUpdate" of resource catalog
                self.catalog['lastUpdate'] = time.time()
                catalog_file = open(self.catalog_file, "w")
                json.dump(self.catalog, catalog_file)
                return 'Registered successfully'
            except:
                return 'An error occurred during registration of Resource'


if __name__ == '__main__':
    res_cat_server = TLCatalogManager('resource_catalog_info.json')

    resource_info = json.load(open('resource_catalog_info.json'))
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.tree.mount(res_cat_server, '/', conf)
    cherrypy.config.update(conf)
    cherrypy.config.update({'server.socket_host': resource_info['ip_address']})
    cherrypy.config.update({"server.socket_port": int(resource_info['ip_port'])})
    cherrypy.engine.start()
    cherrypy.engine.block()
