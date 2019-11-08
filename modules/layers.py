import torch
from torch.nn import functional as F
from torch.nn import Sequential, Linear, ReLU, Sigmoid, Tanh, Identity, Dropout, Conv1d, ConstantPad1d, BatchNorm1d, LSTMCell


def get_activation(name):
    """Get activation function by name."""
    return {
        'relu': ReLU(),
        'sigmoid': Sigmoid(),
        'tanh': Tanh(),
        'identity': Identity()
    }[name]


class ZoneoutLSTMCell(torch.nn.LSTMCell):
    """Wrapper around LSTM cell providing zoneout regularization."""

    def __init__(self, input_size, hidden_size, zoneout_rate_hidden, zoneout_rate_cell, bias=True):
        super(ZoneoutLSTMCell, self).__init__(input_size, hidden_size, bias)
        self.zoneout_c = zoneout_rate_cell
        self.zoneout_h = zoneout_rate_hidden

    def forward(self, cell_input, h, c):
        new_h, new_c = super(ZoneoutLSTMCell, self).forward(cell_input, (h, c))
        if self.training:
            new_h = (1-self.zoneout_h) * F.dropout(new_h - h, self.zoneout_h) + h
            new_c = (1-self.zoneout_c) * F.dropout(new_c - c, self.zoneout_c) + c
        else:
            new_h = self.zoneout_h * h + (1-self.zoneout_h) * new_h
            new_c = self.zoneout_c * c + (1-self.zoneout_c) * new_c
        return new_h, new_c


class DropoutLSTMCell(torch.nn.LSTMCell):
    """Wrapper around LSTM cell providing hidden state dropout regularization."""

    def __init__(self, input_size, hidden_size, dropout_rate, bias=True):
        super(DropoutLSTMCell, self).__init__(input_size, hidden_size, bias)
        self._dropout = Dropout(dropout_rate)

    def forward(self, cell_input, h, c):
        new_h, new_c = super(DropoutLSTMCell, self).forward(cell_input, (h, c))
        new_h = self._dropout(new_h)
        return new_h, new_c


class ConvBlock(torch.nn.Module):
    """One dimensional convolution with batchnorm and dropout, expected channel-first input.
    
    Keyword arguments:
    input_channels -- number if input channels
    output_channels -- number of output channels<F4>
    kernel -- convolution kernel size ('same' padding is used)
    dropout -- dropout rate to be aplied after the block
    activation (optional) -- name of the activation function applied after batchnorm (default 'identity')
    """

    def __init__(self, input_channels, output_channels, kernel, dropout=0.0, activation='identity'):
        super(ConvBlock, self).__init__()
        p = (kernel-1)//2 
        padding = p if kernel % 2 != 0 else (p, p+1)
        self._block = Sequential(
            ConstantPad1d(padding, 0.0),
            Conv1d(input_channels, output_channels, kernel, padding=0, bias=False),
            BatchNorm1d(output_channels),
            get_activation(activation),
            Dropout(dropout)
        )

    def forward(self, x):
        return self._block(x)