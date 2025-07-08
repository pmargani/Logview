# import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from astropy.time import Time

class PlotData:
    """
    Container for x and y data to be plotted.
    """
    def __init__(self, x, y_list, x_col, y_cols, sampler_name, date_plot=False):
        self.x = x
        self.y_list = y_list  # list of y arrays
        self.x_col = x_col
        self.y_cols = y_cols  # list of y column names
        self.date_plot = date_plot
        self.sampler_name = sampler_name

    def __repr__(self):
        return f"PlotData(x={self.x}, y_list={self.y_list})"
    

    def plot_data(self):
        fig = Figure(figsize=(4, 3))
        ax = fig.add_subplot(111)
        if self.date_plot:
            x_mjd = Time(self.x, format='mjd').datetime
            for y, y_col in zip(self.y_list, self.y_cols):
                ax.plot_date(x_mjd, y, '-', label=y_col)
            ax.set_xlabel(x_mjd[0].strftime('%Y-%m-%d %H:%M:%S'))
        else:
            ax.set_xlabel(self.x_col)
            for y, y_col in zip(self.y_list, self.y_cols):
                ax.plot(self.x, y, label=y_col)
        ax.set_title(self.sampler_name)
        ax.set_ylabel(', '.join(self.y_cols))
        ax.legend()
        return fig, ax