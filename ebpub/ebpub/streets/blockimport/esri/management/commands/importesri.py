from django.core.management.base import BaseCommand, CommandError
from ebpub.streets.blockimport.esri import importers

class Command(BaseCommand):
    help = 'Import a shapefile from the ESRI data'
    
    def handle(self, *args, **options):
        if len(args) != 3:
            raise CommandError('Usage: import_esri <importer_type> <city> </path/to/shapefile/>')
        (importer_type, city, shapefile) = args
        importer_mod = getattr(importers, importer_type, None) 
        if importer_mod is None:
            raise CommandError('Invalid importer_type %s' % importer_type)
        importer_cls = getattr(importer_mod, 'EsriImporter', None)
        if importer_cls is None:
            raise CommandError('importer module must define an EsriImporter class')
        importer = importer_cls(shapefile, city)
        if options['verbosity'] == 2:
            verbose = True
        else:
            verbose = False
        num_created = importer.save(verbose)
        if options['verbosity'] > 0:
            print 'Created %d %s(s)' % (num_created, importer_type)
