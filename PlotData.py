# import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from astropy.time import Time
import itertools
from matplotlib import cm

class PlotData:
    """
    Container for x and y data to be plotted.
    """
    def __init__(self, x, y_list, x_col, y_cols, y_expr, sampler_name, col_units, y2_list=None, y2_cols=None, y2_expr=None, date_plot=False):
        self.x = x
        self.y_list = y_list  # list of y arrays
        self.x_col = x_col
        self.y_cols = y_cols  # list of y column names
        self.y_expr  = y_expr 
        self.date_plot = date_plot
        self.sampler_name = sampler_name
        self.col_units = col_units  # dictionary of column units

        self.y2_list = y2_list if y2_list is not None else []  # list of second y arrays
        self.y2_cols = y2_cols if y2_cols is not None else []   # list of second y column names
        self.y2_expr = y2_expr 

    def __repr__(self):
        return f"PlotData(x={self.x}, y_list={self.y_list})"
    

    def plot_data(self):

        fig = Figure(figsize=(4, 3))
        ax = fig.add_subplot(111)
        ax2 = None

        # Generate distinct colors for all plots
        num_plots = len(self.y_list) + len(self.y2_list)
        color_map = cm.get_cmap('tab10' if num_plots <= 10 else 'tab20', num_plots)
        color_iter = iter(color_map.colors)

        if self.date_plot:
            x_mjd = Time(self.x, format='mjd').datetime
            for y, y_col in zip(self.y_list, self.y_cols):
                color = next(color_iter)
                print("plot_date for y_col", y_col)
                label = f"{y_col} ({self.col_units.get(y_col, '')})"
                ax.plot_date(x_mjd, y, '-', label=label, color=color)
            ax.set_xlabel(x_mjd[0].strftime('%Y-%m-%d %H:%M:%S'))
        else:
            ax.set_xlabel(self.x_col)
            for y, y_col in zip(self.y_list, self.y_cols):
                color = next(color_iter)
                label = f"{y_col} ({self.col_units.get(y_col, '')})"
                ax.plot(self.x, y, label=label, color=color)
        label = ", ".join(self.y_cols)
        label = f"({label}){self.y_expr}" if self.y_expr else label    
        ax.set_ylabel(label)

        # Plot y2_list on a secondary y-axis if present
        if len(self.y2_list) >0 and self.y2_cols:
            ax2 = ax.twinx()
            if self.date_plot:
                for y2, y2_col in zip(self.y2_list, self.y2_cols):
                    color = next(color_iter)
                    print("plot_date for y2_col", y2_col)
                    label = f"{y2_col} ({self.col_units.get(y2_col, '')})"
                    ax2.plot_date(x_mjd, y2, '--', label=label, color=color)
            else:
                for y2, y2_col in zip(self.y2_list, self.y2_cols):
                    color = next(color_iter)
                    label = f"{y2_col} ({self.col_units.get(y2_col, '')})"
                    ax2.plot(self.x, y2, '--', label=label, color=color)
            # ax2.set_ylabel(', '.join(self.y2_cols))
            label = ", ".join(self.y2_cols)
            label = f"({label}){self.y2_expr}" if self.y2_expr else label    
            ax2.set_ylabel(label)
            # Combine legends from both axes
            lines, labels = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax2.legend(lines + lines2, labels + labels2)
        else:
            ax.legend()

        ax.set_title(self.sampler_name)
        return fig, ax2 if ax2 else ax