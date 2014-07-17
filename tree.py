#!/usr/bin/env python
# -*- coding: utf-8 -*-
# tree.py
#
# Author: Yann KOETH
# Created: Wed Jul 16 16:20:49 2014 (+0200)
# Last-Updated: Thu Jul 17 17:03:55 2014 (+0200)
#           By: Yann KOETH
#     Update #: 44
#

from collections import defaultdict

class Tree(defaultdict):

    def __init__(self, parent=None):
        self.parent = parent
        super(Tree, self).__init__(lambda: Tree())

    def walk(self):
        for node, children in self.iteritems():
            yield node
            for n in children.walk():
                yield n

    def map(self, param, func):
        for node, children in self.iteritems():
            children.map(func(node, param), func)

    def fromQStandardItemModel(self, model, table):
        def getChildren(node):
            """Return the children tree of node.
            """
            tree = Tree()
            childCount = node.rowCount()
            for i in xrange(childCount):
                child = node.child(i)
                tree[Node(child.text(), table[child.data()])] = getChildren(child)
            return tree

        for i in xrange(model.rowCount()):
            rootItem = model.itemFromIndex(model.index(i, 0))
            self[Node(rootItem.text(), table[rootItem.data()])] = getChildren(rootItem)

class Node:
    def __init__(self, name, data=None):
        self.name = name
        self.data = data

    def __hash__(self):
        return hash((self.name, str(self.data)))

    def __eq__(self, other):
        print self.name, self.data
        print other.name, other.data
        return (self.name == other.name) and (self.data == other.data)

    def __repr__(self):
        return '[Node name={} data={}]'.format(self.name, self.data)
