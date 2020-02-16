from mesh.resource import *

__all__ = ('StandardController',)

class StandardController(Controller):
    """The standard controller."""

    def _prune_resource(self, resource, data, _empty=[]):
        include = data.get('include') or _empty
        exclude = data.get('exclude') or _empty
        if not (include or exclude):
            return resource

        pruned = {}
        for name, value in resource.iteritems():
            field = self.resource.schema[name]
            if field.is_identifier:
                pruned[name] = value
            elif name not in exclude:
                if not (field.deferred and name not in include):
                    pruned[name] = value

        return pruned
