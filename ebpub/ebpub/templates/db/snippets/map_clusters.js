{# This snippet requires these variables: all_bunches, newsitem_list #}

var bunches = {{ all_bunches|safe }};

{% comment %}
An object mapping newsitem ids to attributes about those newsitems.
Example:
{
  12345: {"schema_id": 10},
  23456: {"schema_id": 4},
  ...
}
{% endcomment %}
eb.newsitems = {% templatetag openbrace %}{% for ni in newsitem_list %}{{ ni.id }}: {% templatetag openbrace %}"schema_id": {{ ni.schema.id }}{% templatetag closebrace %}{% if not forloop.last %}, {% endif %}{% endfor %}{% templatetag closebrace %};

var extractIds = function() {
    var ids = [];
    for (var key in eb.newsitems) {
	ids.push(key);
    }
    return ids;
};

var contentFetcher = eb.makeAjaxContentFetcher(extractIds(), map);

var clusterLayer = new eb.ClusterLayer("clusters", null, contentFetcher)
clusterLayer.addBunches(bunches);
map.addLayer(clusterLayer);
