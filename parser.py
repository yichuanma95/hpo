import networkx as nx
import obonet
from collections import defaultdict
import re
import os


def get_synonyms(data):
    """Format synonyms as dicionary
    exact and related synonyms are the keys, and their values are in lists
    """
    if 'synonym' in data:
        syn_dict = {}
        exact = []
        related = []
        broad = []
        for syn in data['synonym']:
            if 'EXACT' in syn:
                match = re.findall(r'\"(.+?)\"', syn)
                exact = exact + match
            elif 'RELATED' in syn:
                match = re.findall(r'\"(.+?)\"', syn)
                related = related + match
            elif 'BROAD' in syn:
                match = re.findall(r'\"(.+?)\"', syn)
                broad = broad + match
        synonyms = {}
        if len(exact) > 0:
            synonyms["exact"] = exact
        if len(related) > 0:
            synonyms["related"] = related
        if len(broad) > 0:
            synonyms["broad"] = broad
        return synonyms
    else:
        return {}


def load_data(data_folder):
    annotations = {}
    infile = os.path.join(data_folder, 'phenotype_to_genes.txt')
    assert os.path.exists(infile)
    with open(infile) as f:
        f.readline()  # first line is just a header
        for line in f:
            datapoint = line.rstrip('\n').split('\t')
            hpoID = datapoint[0]
            entrezGeneID = datapoint[2]
            entrezGeneSymbol = datapoint[3]
            sourceInfo = datapoint[4]
            source = datapoint[5]
            diseaseID = datapoint[6]
            obj = {
                'gene': {
                    'id': entrezGeneID,
                    'symbol': entrezGeneSymbol
                },
                'source': source,
                'disease_id': diseaseID
            }
            if sourceInfo != '' and sourceInfo != '-':
                obj['source_info'] = sourceInfo
            annotations.setdefault(hpoID, []).append(obj)

    url = "https://raw.githubusercontent.com/obophenotype/human-phenotype-ontology/master/hp.obo"
    graph = obonet.read_obo(url)
    for item in graph.nodes():
        rec = graph.nodes[item]
        rec["_id"] = item
        rec["hp"] = item
        if rec.get("is_a"):
            rec["parents"] = [parent for parent in rec.pop("is_a") if parent.startswith("HP:")]
        if rec.get("xref"):
            xrefs = defaultdict(set)
            for val in rec.get("xref"):
                if ":" in val:
                    prefix, id = val.split(':', 1)
                    if prefix in ["http", "https"]:
                        continue
                    if prefix.lower() in ['umls', 'snomedct_us', 'snomed_ct', 'cohd', 'ncit']:
                        xrefs[prefix.lower()].add(id)
                    elif prefix == 'MSH':
                        xrefs['mesh'].add(id)
                    else:
                        xrefs[prefix.lower()].add(val)
            for k, v in xrefs.items():
                xrefs[k] = list(v)
            rec.pop("xref")
            rec["xrefs"] = dict(xrefs)
        rec["children"] = [child for child in graph.predecessors(item) if child.startswith("HP:")]
        rec["ancestors"] = [ancestor for ancestor in nx.descendants(graph, item) if ancestor.startswith("HP:")]
        rec["descendants"] = [descendant for descendant in nx.ancestors(graph, item) if descendant.startswith("HP:")]
        rec["synonym"] = get_synonyms(rec)
        if rec.get("created_by"):
            rec.pop("created_by")
        if rec.get("creation_date"):
            rec.pop("creation_date")
        if rec.get("relationship"):
            for rel in rec.get("relationship"):
                predicate, val = rel.split(' ')
                prefix = val.split(':')[0]
                rec[predicate] = {prefix.lower(): val}
            rec.pop("relationship")

        if annotations.get(item):
            rec["annotations"] = annotations[item]

        yield rec
