#import logging
#from datetime import datetime
#
#class Formatter(logging.Formatter):
#    def format(self, record):
#        record.timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
#        try:
#            description = record.description
#        except AttributeError:
#            record.description = ''
#        else:
#            record.description = '\n' + repr(description)
#        return logging.Formatter.format(self, record)
#
#log = logging.getLogger('mesh')
#log.setLevel(logging.DEBUG)
#handler = logging.StreamHandler()
#handler.setFormatter(Formatter('%(timestamp)s %(name)s %(levelname)s %(message)s%(description)s'))
#log.addHandler(handler)
