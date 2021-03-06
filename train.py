#!/usr/bin/env python3

"""
Example training program for b-tagging with keras
"""

import h5py
from argparse import ArgumentParser
import numpy as np
from itertools import cycle

import keras
from keras import layers
from keras.models import Model

def get_args():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('input_file')
    return parser.parse_args()

def flatten(ds):
    ftype = [(n, float) for n in ds.dtype.names]
    flat = ds.astype(ftype).view(float).reshape(ds.shape + (-1,))
    return flat
    # return flat.swapaxes(1, len(ds.shape))

def run():
    args = get_args()

    jet_vars = ['pt', 'eta']
    trk_vars = ['d0', 'charge']
    def generate(batch_size=100):
        with h5py.File(args.input_file, 'r') as hdf_file:
            n_jets = hdf_file['jets'].shape[0]
            limit = n_jets - batch_size
            all_jets = hdf_file['jets']
            all_tracks = hdf_file['tracks']
            for start_index in cycle(range(0, limit, batch_size)):
                sl = slice(start_index,start_index + batch_size)
                jets = all_jets[sl]
                tracks = all_tracks[sl,:]

                fl_jets = flatten(jets[jet_vars])
                fl_trks = flatten(tracks[trk_vars])
                labels = jets['LabDr_HadF']
                charge = jets['mv2c10']
                one_hot = np.vstack([labels == n for n in [0, 4, 5, 15]]).T
                yield [fl_trks, fl_jets], [one_hot, charge]

    model = get_model(len(jet_vars), len(trk_vars))
    # for (trk, jets), (targets, charge) in generate():
    #     print(trk.shape, jets.shape, targets.shape, charge.shape)

    model.fit_generator(generate(), steps_per_epoch=1000)


def get_model(n_vx_vars, n_trk_var):

    # setup inputs
    tracks = layers.Input(shape=(60, n_trk_var), name='tracks')
    vertex = layers.Input(shape=(n_vx_vars,), name='vertices')

    # add GRU to process tracks
    gru = layers.GRU(5)(tracks)

    # merge with the vertex inputs and feed to a dense layer
    merged = layers.concatenate([gru, vertex])
    dense = layers.Dense(10, activation='relu')(merged)

    # add flavors output
    flavor = layers.Dense(4, activation='softmax', name='flavor')(dense)

    # add charge output
    charge = layers.Dense(1, name='charge')(dense)

    # build and compile the model
    model = Model(inputs=[tracks, vertex], outputs=[flavor, charge])
    model.compile(optimizer='adam',
                  loss=['categorical_crossentropy', 'mean_squared_error'],
                  metrics=['accuracy', 'accuracy'])
    return model

if __name__ == '__main__':
    run()
