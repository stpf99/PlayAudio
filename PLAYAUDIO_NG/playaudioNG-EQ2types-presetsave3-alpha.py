import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, GdkPixbuf, Gst
import os
import eyed3

Gst.init(None)

class MusicPlayerWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Music Player with Equalizer")
        self.set_default_size(600, 500)
        
        self.current_playlist_store_index = -1
        self.playlist_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str, str, str)
        self.current_cover = Gtk.Image()
        self.eq_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.init_gstreamer()
        self.init_ui()
        
    def init_ui(self):
        hbox_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(hbox_top)

        vbox_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox_top.pack_start(vbox_left, True, True, 0)

        self.create_menu(vbox_left)
        self.create_playlist_view(vbox_left)
        self.create_controls(vbox_left)
        self.create_equalizer(vbox_left)
        self.create_playlist_names(vbox_left)

        vbox_right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox_top.pack_start(vbox_right, False, False, 0)

        self.create_cover_art(vbox_right)

    def create_menu(self, vbox):
        menubar = Gtk.MenuBar()
        vbox.pack_start(menubar, False, False, 0)
        
        filemenu = Gtk.Menu()
        filem = Gtk.MenuItem(label="File")
        filem.set_submenu(filemenu)
        
        openm = Gtk.MenuItem(label="Open")
        openm.connect("activate", self.on_open_clicked)
        filemenu.append(openm)
        
        folderm = Gtk.MenuItem(label="Open Folder")
        folderm.connect("activate", self.on_load_folder_clicked)
        filemenu.append(folderm)

        m3um = Gtk.MenuItem(label="Open M3U Playlist")
        m3um.connect("activate", self.on_load_m3u_clicked)
        filemenu.append(m3um)
        
        quitm = Gtk.MenuItem(label="Quit")
        quitm.connect("activate", Gtk.main_quit)
        filemenu.append(quitm)
        
        menubar.append(filem)

    def create_playlist_view(self, vbox):
        self.treeview = Gtk.TreeView(model=self.playlist_store)
        self.treeview.set_activate_on_single_click(True)
        self.treeview.connect("row-activated", self.on_row_activated)
        
        renderer = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn("Cover", renderer)
        column.set_cell_data_func(renderer, self.cover_data_func)
        self.treeview.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Title", renderer, text=2)
        self.treeview.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Artist", renderer, text=3)
        self.treeview.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Album", renderer, text=4)
        self.treeview.append_column(column)
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.treeview)
        vbox.pack_start(scrolled_window, True, True, 0)
        
    def create_controls(self, vbox):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)
        
        self.play_button = Gtk.Button(label="Play")
        self.play_button.connect("clicked", self.on_play_clicked)
        hbox.pack_start(self.play_button, False, False, 0)
        
        self.stop_button = Gtk.Button(label="Stop")
        self.stop_button.connect("clicked", self.on_stop_clicked)
        hbox.pack_start(self.stop_button, False, False, 0)
        
        self.prev_button = Gtk.Button(label="Previous")
        self.prev_button.connect("clicked", self.on_prev_clicked)
        hbox.pack_start(self.prev_button, False, False, 0)
        
        self.next_button = Gtk.Button(label="Next")
        self.next_button.connect("clicked", self.on_next_clicked)
        hbox.pack_start(self.next_button, False, False, 0)
        
        self.volume_control = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.volume_control.set_value(50)
        self.volume_control.connect("value-changed", self.on_volume_changed)
        hbox.pack_start(self.volume_control, True, True, 0)
        
        self.statusbar = Gtk.Statusbar()
        vbox.pack_start(self.statusbar, False, False, 0)
        
    def create_equalizer(self, vbox):
        self.equalizer_type = "10bands"
        self.equalizer_sliders = []
        self.file_path = []
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)
        
        self.radio_10bands = Gtk.RadioButton.new_with_label_from_widget(None, "10 Bands")
        self.radio_10bands.connect("toggled", self.on_equalizer_selected, "10bands")
        hbox.pack_start(self.radio_10bands, False, False, 0)
        
        self.radio_3bands = Gtk.RadioButton.new_with_label_from_widget(self.radio_10bands, "3 Bands")
        self.radio_3bands.connect("toggled", self.on_equalizer_selected, "3bands")
        hbox.pack_start(self.radio_3bands, False, False, 0)
        
        self.eq_slider_box = Gtk.Box()
        vbox.pack_start(self.eq_slider_box, False, False, 0)
        
        self.update_equalizer_sliders()
        
    def create_cover_art(self, vbox):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, False, False, 0)

        self.current_cover = Gtk.Image()
        hbox.pack_start(self.current_cover, False, False, 0)

        self.playlists_listbox = Gtk.ListBox()
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.playlists_listbox)
        vbox.pack_start(scrolled_window, True, True, 0)
         
    def create_playlist_names(self, vbox):
        self.playlists_listbox = Gtk.ListBox()
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.playlists_listbox)
        vbox.pack_start(scrolled_window, False, False, 0)
    
    def init_gstreamer(self):
        self.player = Gst.ElementFactory.make("playbin", "player")
        self.equalizer_10bands = Gst.ElementFactory.make("equalizer-10bands", "equalizer_10bands")
        self.equalizer_3bands = Gst.ElementFactory.make("equalizer-3bands", "equalizer_3bands")
        
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self.on_about_to_finish)
        
    def on_open_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(title="Please choose a file", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            self.add_file_to_playlist(file_path)
            self.load_equalizer_preset(file_path)
        dialog.destroy()
        
    def add_file_to_playlist(self, file_path):
        try:
            audio = eyed3.load(file_path)
            if audio is not None:
                title = audio.tag.title if audio.tag.title else 'Unknown'
                artist = audio.tag.artist if audio.tag.artist else 'Unknown'
                album = audio.tag.album if audio.tag.album else 'Unknown'
                
                try:
                    cover_data = audio.tag.images[0].image_data
                    loader = GdkPixbuf.PixbufLoader()
                    loader.write(cover_data)
                    loader.close()
                    cover = loader.get_pixbuf()
                except (IndexError, eyed3.Error):
                    cover = None
                    
                self.playlist_store.append([cover, file_path, title, artist, album])  # Zmiana na playlist_store
            else:
                self.playlist_store.append([None, file_path, os.path.basename(file_path), 'Unknown', 'Unknown'])  # Zmiana na playlist_store
        except eyed3.Error:
                self.playlist_store.append([None, file_path, os.path.basename(file_path), 'Unknown', 'Unknown'])  # Zmiana na playlist_store

            
    def on_load_folder_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(title="Please choose a folder", parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder_path = dialog.get_filename()
            self.add_files_from_folder(folder_path)
        dialog.destroy()
        
    def add_files_from_folder(self, folder_path):
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith(".mp3") or file.endswith(".wav") or file.endswith(".ogg"):
                    file_path = os.path.join(root, file)
                    self.add_file_to_playlist(file_path)
    
    def on_load_m3u_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(title="Please choose an M3U playlist file", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_filter(self.create_m3u_filter())
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            m3u_path = dialog.get_filename()
            self.load_m3u_playlist(m3u_path)
        dialog.destroy()
        
    def create_m3u_filter(self):
        filter_m3u = Gtk.FileFilter()
        filter_m3u.set_name("M3U Playlist")
        filter_m3u.add_pattern("*.m3u")
        return filter_m3u
    
    def load_m3u_playlist(self, m3u_path):
        base_path = os.path.dirname(m3u_path)
        with open(m3u_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    file_path = os.path.join(base_path, line)
                    if os.path.exists(file_path):
                        self.add_file_to_playlist(file_path)
                    else:
                        print(f"File {file_path} does not exist or is not accessible.")

        # Get the playlist name from the M3U file name
        playlist_name = os.path.splitext(os.path.basename(m3u_path))[0]
        # Add the playlist name to the list
        row = Gtk.ListBoxRow()
        label = Gtk.Label(label=playlist_name)
        row.add(label)
        self.playlists_listbox.add(row)
        label.connect("activate-link", self.on_playlist_name_clicked, m3u_path)

    def on_playlist_name_clicked(self, widget, m3u_path):
        self.on_stop_clicked(None)
        self.playlist_store.clear()  # Zakładając, że `self.playlist_store` jest `Gtk.ListStore`
        self.load_m3u_playlist(m3u_path)
         
    def cover_data_func(self, column, cell, model, iter, data):
        pixbuf = model.get_value(iter, 0)
        if pixbuf is not None:
            thumbnail = pixbuf.scale_simple(25, 25, GdkPixbuf.InterpType.BILINEAR)
            cell.set_property("pixbuf", thumbnail)
        else:
            cell.set_property("pixbuf", None)
            
    def on_row_activated(self, treeview, path, column):
        self.on_stop_clicked(self)
        iter = treeview.get_model().get_iter(path)
        self.current_playlist_index = path.get_indices()[0]
        file_path = treeview.get_model().get_value(iter, 1)
        cover = treeview.get_model().get_value(iter, 0)
        self.load_and_play_file(file_path)
        if cover is not None:
            self.current_cover.set_from_pixbuf(cover.scale_simple(150, 150, GdkPixbuf.InterpType.BILINEAR))
        else:
            self.current_cover.clear()

    def on_prev_clicked(self, widget):
        self.on_stop_clicked(self)
        if self.current_playlist_store_index > 0:
            self.current_playlist_store_index -= 1
            iter = self.playlist_store.get_iter(Gtk.TreePath(self.current_playlist_store_index))
            file_path = self.playlist_store.get_value(iter, 1)
            self.load_and_play_file(file_path)
            
    def on_next_clicked(self, widget):
        self.on_stop_clicked(self)
        if self.current_playlist_store_index < len(self.playlist_store) - 1:
            self.current_playlist_store_index += 1
            iter = self.playlist_store.get_iter(Gtk.TreePath(self.current_playlist_store_index))
            file_path = self.playlist_store.get_value(iter, 1)
            self.load_and_play_file(file_path)
            
    def on_volume_changed(self, widget):
        volume = widget.get_value() / 100.0
        self.player.set_property("volume", volume)
        
    def on_about_to_finish(self, bus, msg):
        self.on_next_clicked(None)
        
    def on_equalizer_selected(self, widget, equalizer_type):
        if widget.get_active():
            self.equalizer_type = equalizer_type
            self.update_equalizer_sliders()
            
    def load_and_play_file(self, file_path):
        self.player.set_property("uri", "file://" + file_path)
        self.player.set_state(Gst.State.PLAYING)
        
    def on_play_clicked(self, widget):
        self.on_stop_clicked(self)
        self.player.set_state(Gst.State.PLAYING)
        
    def on_stop_clicked(self, widget):
        self.player.set_state(Gst.State.NULL)
        
    def update_equalizer_sliders(self):
        for slider in self.equalizer_sliders:
            slider.destroy()
        self.equalizer_sliders = []

        if self.equalizer_type == "10bands":
            bands = 10
            eq = self.equalizer_10bands
        else:
            bands = 3
            eq = self.equalizer_3bands

        for i in range(bands):
            adj = Gtk.Adjustment(value=0, lower=-24, upper=12, step_increment=0.1, page_increment=1, page_size=0)
            slider = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL, adjustment=adj)
            slider.set_value_pos(Gtk.PositionType.TOP)
            slider.set_size_request(30, 150)
            slider.connect("value-changed", self.on_eq_slider_changed, i, eq)
            self.eq_slider_box.pack_start(slider, False, False, 0)
            self.equalizer_sliders.append(slider)
            if eq:
                value = eq.get_property(f"band{i}")
                slider.set_value(value)

        self.show_all()

    def on_eq_slider_changed(self, widget, band, eq):
        value = widget.get_value()
        eq.set_property(f"band{band}", value)
        self.player.set_property("audio-filter", eq)
        self.save_equalizer_preset(band)

    def load_equalizer_preset(self, file_path):
        preset_file = f"{file_path}.eqpreset"
        if os.path.exists(preset_file):
            with open(preset_file, "r") as f:
                preset = f.readlines()
            for i, line in enumerate(preset):
                if self.equalizer_type == "10bands" and i < 10:
                    self.equalizer_10bands.set_property(f"band{i}", float(line.strip()))
                elif self.equalizer_type == "3bands" and i < 3:
                    self.equalizer_3bands.set_property(f"band{i}", float(line.strip()))
            self.update_equalizer_sliders()

    def save_equalizer_preset(self, file_path):
        preset_file = f"{file_path}.eqpreset"
        with open(preset_file, "w") as f:
            if self.equalizer_type == "10bands":
                for i in range(10):
                    f.write(f"{self.equalizer_10bands.get_property(f'band{i}')}\n")
            elif self.equalizer_type == "3bands":
                for i in range(3):
                    f.write(f"{self.equalizer_3bands.get_property(f'band{i}')}\n")

    def update_cover_position(self):
        vbox_children = self.get_children()
        if len(vbox_children) > 2:
            hbox_eq_cover = vbox_children[-2]
            if hbox_eq_cover:
                hbox_eq_cover.reorder_child(self.current_cover, 1)
                self.show_all()

win = MusicPlayerWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
