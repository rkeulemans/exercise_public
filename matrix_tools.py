import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl

def matrix_to_image(matrix, filename, grid=True, values_in_cells=False, axis_indices=True, axis_titles=False):
    fig, ax = plt.subplots()
    
    if grid:
        # Minor ticks
        ax.set_xticks(np.arange(-.5, 10, 1), minor=True)
        ax.set_yticks(np.arange(-.5, 10, 1), minor=True)
        ax.grid(which='minor', color='black', linestyle='-', linewidth=2)
    else:
        plt.axis('off')
    
    if values_in_cells:
        import matplotlib.patheffects as pe
        for (i, j), z in np.ndenumerate(matrix):
            value = ""
            try:
                value = int(z)
            except:
                value = ""
            ax.text(j, i, '{}'.format(value), ha='center', va='center', path_effects=[pe.withStroke(linewidth=4, foreground="white")]) 
        
    if axis_indices: 
        ax.set_xticklabels([i for i in range(0, 9)])
        ax.set_yticklabels([i for i in range(0, 9)])
        
    if axis_titles:
        ax.set_xlabel("column index")
        ax.xaxis.set_label_position('top')

        ax.set_ylabel("row index")
        ax.yaxis.set_label_position('left') 

    import copy
    cmap = copy.copy(mpl.cm.get_cmap("gray_r"))
    cmap.set_bad(color='red')
    # was .matshow
    ax.matshow(matrix, cmap=cmap)
    
    plt.savefig("{}.png".format(filename), dpi=200, bbox_inches='tight')
    plt.close(fig)
    
    