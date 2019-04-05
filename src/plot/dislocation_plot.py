import numpy as num

km = 1000.

def draw(
        dislocation,
        coordinates,
        axes=None,
        cmap='coolwarm',
        zero_center=False):
    if axes is not None:
        if zero_center:
            vmax = num.max(num.abs([
                num.min(dislocation), num.max(dislocation)]))
            vmin = -vmax
        else:
            vmax = num.max(dislocation)
            vmin = num.min(dislocation)
        scat = axes.scatter(
            coordinates[:, 1] * 1. / km,
            coordinates[:, 0] * 1. / km,
            c=dislocation,
            cmap=cmap,
            edgecolor='None',
            vmin=vmin, vmax=vmax)

        return scat

def setup_axes(axes=None, title='', xlabeling=False, ylabeling=False):
    if axes is not None:
        axes.set_title(title)
        axes.grid(True)
        if xlabeling:
            axes.set_xlabel('Easting [$km$]')
        if ylabeling:
            axes.set_ylabel('Northing [$km$]')


def plot(
        dislocations,
        coordinates,
        filename=None,
        dpi=100,
        fontsize=10.,
        figsize=None,
        titles=None,
        cmap='coolwarm',
        zero_center=False):

    from matplotlib import pyplot as plt
    from pyrocko.plot import mpl_init, mpl_margins, mpl_papersize

    assert dislocations.shape[1] >= 3
    assert coordinates.shape[0] == dislocations.shape[0]

    mpl_init(fontsize=fontsize)

    if figsize is None:
        figsize = mpl_papersize('a4', 'landscape')

    fig = plt.figure(figsize=figsize)
    labelpos = mpl_margins(
        fig,
        left=7., right=5., top=5., bottom=6., nw=2, nh=2,
        wspace=6., hspace=5., units=fontsize)

    if not titles:
        titles = [
            'Displacement North',
            'Displacement East',
            'Displacement Down',
            '||Displacement||']

    assert len(titles) == 4

    data = dislocations[:, :3]
    data = num.hstack((data, num.linalg.norm(data, axis=1)[:, num.newaxis]))

    for iax in range(1, 5):
        axes = fig.add_subplot(2, 2, iax)
        labelpos(axes, 2., 2.5)

        setup_axes(
            axes=axes,
            title=titles[iax - 1],
            xlabeling=False if iax < 3 else True,
            ylabeling=False if iax in [2, 4] else True)

        scat = draw(
            num.squeeze(data[:, iax - 1]),
            coordinates,
            axes=axes,
            cmap=cmap,
            zero_center=zero_center)
        cbar = fig.colorbar(scat)
        cbar.set_label('[$m$]')

    if filename:
        fig.savefig(filename, dpi=dpi)
    else:
        plt.show()
