# Copyright (C) 2011 by Florian Mayer <flormayer@aim.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from copy import deepcopy, copy

from burrahobbit._tree import (
    NULLNODE, GET, ASSOC, IASSOC, WITHOUT, doc, DispatchNode
)

class SetNode(object):
    """ A AssocNode contains the actual key-value mapping. """
    __slots__ = ['key', 'hsh']
    def __init__(self, key):
        self.key = key
        self.hsh = hash(key)
    
    def xor(self, hsh, shift, node):
        if node.key == self.key:
            return NULLNODE
        else:
            return self.assoc(hsh, shift, node)
    
    @doc(GET)
    def get(self, hsh, shift, key):
        # If the key does not match the key of the AssocNode, thus the hash
        # matches to the current level, but it is not the correct node,
        # raise a KeyError, otherwise return the value.
        if key != self.key:
            raise KeyError(key)
        return self
    
    @doc(ASSOC)
    def assoc(self, hsh, shift, node):
        # If there is a hash-collision, return a HashCollisionNode,
        # otherwise return a DispatchNode dispatching depending on the
        # current level (if the two hashes only differ at a higher-level,
        # DispatchNode.make will return a DispatchNode that contains a
        # DispatchNode etc. up until the necessary depth.
        if node.key == self.key:
            return node
        
        if hsh == self.hsh:
            return HashCollisionNode(
                [self, node]
            )
        return DispatchNode.make(shift, [self, node])
    
    @doc(IASSOC)
    def _iassoc(self, hsh, shift, node):
        if node.key == self.key:
            self.key = node.key
            self.value = node.value
            return self
        
        if hsh == self.hsh:
            return HashCollisionNode(
                [self, node]
            )
        return DispatchNode.make(shift, [self, node])        
    
    @doc(WITHOUT)
    def without(self, hsh, shift, key):
        # If the key matches the key of this AssocNode, returning NULLNODE
        # will remove the Node from the map. Otherwise raise a KeyError.
        if key != self.key:
            raise KeyError(key)
        return NULLNODE
    
    _iwithout = without
    
    def __iter__(self):
        yield self
    
    def __copy__(self):
        return SetNode(self.key)


class PersistentTreeSet(object):
    __slots__ = ['root']
    def __init__(self, root=NULLNODE):
        self.root = root
    
    def __contains__(self, key):
        try:
            self.root.get(hash(key), 0, key)
            return True
        except KeyError:
            return False
    
    def __and__(self, other):
        return PersistentTreeSet(self.root & other.root)
    
    def __xor__(self, other):
        return PersistentTreeSet(self.root ^ other.root)
    
    def __or__(self, other):
        return PersistentTreeSet(self.root | other.root)
    
    def add(self, key):
        """ Return copy of self with an association between key and value.
        May override an existing association. """
        return PersistentTreeMap(
            self.root.assoc(hash(key), 0, SetNode(key))
        )
    
    def without(self, key):
        """ Return copy of self with key removed. """
        return PersistentTreeMap(
            self.root.without(hash(key), 0, key)
        )
    
    def __iter__(self):
        for node in self.root:
            yield node.key
    
    @staticmethod
    def from_set(set_):
        """ Create PersistentTreeSet from existing set. """
        mp = VolatileTreeSet()
        for key in set_:
            mp = mp.add(key)
        return mp.persistent()
    
    @staticmethod
    def construct(iterable=None):
        if isinstance(iterable, PersistentTreeSet):
            return PersistentTreeSet(copy(iterable.root))
        if iterable is None:
            return PersistentTreeSet()
        
        return PersistentTreeSet.from_set(iterable)
        
    def volatile(self):
        return VolatileTreeSet(copy(self.root))


class VolatileTreeSet(PersistentTreeSet):
    def add(self, key):
        """ Update this VolatileTreeMap to contain an association between
        key and value.
        
        USE WITH CAUTION: This should only be used if no other reference
        to the PersistentTreeMap may exist. """
        self.root = self.root.assoc(hash(key), 0, SetNode(key))
        return self
    
    def without(self, key):
        """ Remove key.
        
        USE WITH CAUTION: This should only be used if no other reference
        to the PersistentTreeMap may exist. """
        self.root = self.root._iwithout(hash(key), 0, key)
        return self
    
    def persistent(self):
        return PersistentTreeSet(self.root)
