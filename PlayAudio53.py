import gi
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
import os
import random
import time
from urllib.parse import quote
import eyed3
import gi.repository.GdkPixbuf as GdkPixbuf
import gi.repository.Gst as Gst
import numpy as np
import pyaudio
from gi.repository import Gtk, Gdk, GObject, GLib, Pango
import cairo

class MusicPlayer:
    def __init__(self):
        Gst.init(None)

        self.window = Gtk.Window()
        self.window.connect("destroy", Gtk.main_quit)
        self.window.set_default_size(200, 200)
        self.window.set_title("Music Player")
        self.previous_playing_label = Gtk.Label()
        self.previous_playing_label.set_name("previous-playing-label")
        self.previous_playing_label.set_markup('<span font_desc="12">Playing Previous:</span>')
        self.now_playing_label = Gtk.Label()
        self.now_playing_label.set_name("now-playing-label")
        self.now_playing_label.set_markup('<span font_desc="12">Playing:</span>')
        self.next_playing_label = Gtk.Label()
        self.next_playing_label.set_name("next-playing-label")
        self.next_playing_label.set_markup('<span font_desc="12">Playing Next:</span>')
        self.previous_playing_track = None
        self.now_playing_track = None
        self.next_playing_track = None
        self.audio_buffer = bytearray()
        self.buffer_duration = 3  # Czas buforowania w sekundach
        self.buffer_chunk_size = 1024  # Rozmiar bufora
        self.buffer_ready = False

        # Konfiguracja strumienia audio
        self.pa = pyaudio.PyAudio()
        self.stream_audio_input = None
        self.stream_audio_output = None
        self.sample_rate = 44100  # Przykładowa częstotliwość próbkowania
        self.num_channels = 2  # Dwa kanały (stereo)
        self.sample_width = self.pa.get_sample_size(pyaudio.paInt16)
        self.chunk_size = 1024  # Rozmiar paczki audio

        self.playlist_store = Gtk.ListStore(str, str, str, str, str)
        self.original_playlist = []  # Przechowuje oryginalną listę odtwarzania przed filtrowaniem
        self.playlist_view = Gtk.TreeView(model=self.playlist_store)
        # Kolumna "Filename"
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column = Gtk.TreeViewColumn("Filename", renderer, text=0)
        column.set_sort_column_id(0)  # Ustaw identyfikator kolumny dla sortowania
        column.set_sort_indicator(True)  # Wyświetl wskaźnik sortowania w nagłówku kolumny
        column.set_resizable(True)  # Umożliwia zmianę szerokości kolumny przez użytkownika
        self.playlist_view.append_column(column)

        # Kolumna "Title"
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column = Gtk.TreeViewColumn("Title", renderer, text=4)
        column.set_sort_column_id(4)
        column.set_sort_indicator(True)
        column.set_resizable(True)
        self.playlist_view.append_column(column)

        # Kolumna "Artist"
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column = Gtk.TreeViewColumn("Artist", renderer, text=1)
        column.set_sort_column_id(1)
        column.set_sort_indicator(True)
        column.set_resizable(True)
        self.playlist_view.append_column(column)

        # Kolumna "Genre"
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column = Gtk.TreeViewColumn("Genre", renderer, text=2)
        column.set_sort_column_id(2)
        column.set_sort_indicator(True)
        column.set_resizable(True)
        self.playlist_view.append_column(column)

        # Kolumna "Album"
        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column = Gtk.TreeViewColumn("Album", renderer, text=3)
        column.set_sort_column_id(3)
        column.set_sort_indicator(True)
        column.set_resizable(True)
        self.playlist_view.append_column(column)

        self.column_sort_order = Gtk.SortType.ASCENDING  # Domyślny porządek sortowania
        for i in range(5):
            self.playlist_view.get_column(i).set_sort_order(self.column_sort_order)  # Ustaw porządek sortowania dla kolumny

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(self.playlist_view)


        # Create an HPaned container to split the window horizontally
        self.hpaned = Gtk.HPaned()
        vbox = Gtk.VBox(homogeneous=False, spacing=0)
        vbox.pack_start(self.previous_playing_label, False, False, 2)
        vbox.pack_start(self.now_playing_label, False, False, 2)
        vbox.pack_start(self.next_playing_label, False, False, 2)
        vbox.pack_start(self.hpaned, True, True, 0)

        self.window.add(vbox)

        # Create a frame for the playlist
        playlist_frame = Gtk.Frame()
        playlist_frame.set_label("Playlist")
        self.hpaned.pack1(playlist_frame, True, False)

        # Add the scrolled playlist to the frame
        playlist_frame.add(scrolled_window)

        self.album_cover_fixed = Gtk.Fixed()
        size = 300  # Rozmiar obszaru rysowania albumu (kwadratowy)
        self.album_cover_fixed.set_size_request(size, size)  # Ustaw rozmiar obszaru rysowania na kwadratowy
        self.album_cover_fixed.set_property("width-request", size)  # Ustaw szerokość na stałą wartość
        self.album_cover_fixed.set_property("height-request", size)  # Ustaw wysokość na stałą wartość

        # Add the album cover fixed container to the right side of the HPaned
        self.hpaned.pack2(self.album_cover_fixed, False, False)

        self.play_button = Gtk.Button(label="Play")
        self.play_button.connect("clicked", self.play)
        self.pause_button = Gtk.Button(label="Pause")
        self.pause_button.connect("clicked", self.toggle_pause)
        self.stop_button = Gtk.Button(label="Stop")
        self.stop_button.connect("clicked", self.stop)
        self.next_button = Gtk.Button(label="Next")
        self.next_button.connect("clicked", self.play_next_track)

        self.previous_button = Gtk.Button(label="Previous")
        self.previous_button.connect("clicked", self.play_previous_track)
        self.repeat_mode = "off" 
        self.repeat_off_button = Gtk.RadioButton.new_with_label_from_widget(None, "Off")
        self.repeat_off_button.connect("toggled", self.toggle_repeat_mode, "off")
        self.repeat_one_button = Gtk.RadioButton.new_with_label_from_widget(self.repeat_off_button, "Repeat One")
        self.repeat_one_button.connect("toggled", self.toggle_repeat_mode, "one")
        self.repeat_all_button = Gtk.RadioButton.new_with_label_from_widget(self.repeat_off_button, "Repeat All")
        self.repeat_all_button.connect("toggled", self.toggle_repeat_mode, "all")


        self.load_from_dir_button = Gtk.Button(label="Load Dir")
        self.load_from_dir_button.connect("clicked", self.load_from_dir)
        self.append_from_file_button = Gtk.Button(label="Append File")
        self.append_from_file_button.connect("clicked", self.append_from_file)
        self.clear_playlist_button = Gtk.Button(label="Clear Playlist")
        self.clear_playlist_button.connect("clicked", self.clear_playlist)
        self.shuffle_playlist_button = Gtk.Button(label="Shuffle Playlist")
        self.shuffle_playlist_button.connect("clicked", self.shuffle_playlist)
        self.save_playlist_button = Gtk.Button(label="Save Playlist")
        self.save_playlist_button.connect("clicked", self.save_playlist)
        self.load_playlist_button = Gtk.Button(label="Load Playlist")
        self.load_playlist_button.connect("clicked", self.load_playlist)

        self.mute_button = Gtk.ToggleButton(label="Mute")
        self.mute_button.connect("toggled", self.toggle_mute)

        hbox_buttons = Gtk.HBox(homogeneous=False, spacing=0)
        hbox_buttons.pack_start(self.play_button, True, True, 2)
        hbox_buttons.pack_start(self.pause_button, True, True, 2)
        hbox_buttons.pack_start(self.stop_button, True, True, 2)
        hbox_buttons.pack_start(self.next_button, True, True, 2)
        hbox_buttons.pack_start(self.previous_button, True, True, 2)
        hbox_buttons.pack_start(self.load_from_dir_button, True, True, 2)
        hbox_buttons.pack_start(self.append_from_file_button, True, True, 2)
        hbox_buttons.pack_start(self.clear_playlist_button, True, True, 2)
        hbox_buttons.pack_start(self.shuffle_playlist_button, True, True, 2)
        hbox_buttons.pack_start(self.save_playlist_button, True, True, 2)
        hbox_buttons.pack_start(self.load_playlist_button, True, True, 2)
        hbox_buttons.pack_start(self.repeat_off_button, True, True, 2)
        hbox_buttons.pack_start(self.repeat_all_button, True, True, 2)
        hbox_buttons.pack_start(self.repeat_one_button, True, True, 2)
        hbox_buttons.pack_start(self.mute_button, True, True, 2)

        self.time_label = Gtk.Label(label="00:00:00 / 00:00:00")
        self.time_label.set_name("time-label")
        hbox_buttons.pack_start(self.time_label, False, False, 2)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search...")
        self.search_entry.connect("activate", self.search_playlist)

        # Dodaj rozwijalną listę dla typu wyszukiwania
        self.search_type_combo = Gtk.ComboBoxText()
        self.search_type_combo.append_text("Title")
        self.search_type_combo.append_text("Artist")
        self.search_type_combo.append_text("Genre")
        self.search_type_combo.append_text("Album")
        self.search_type_combo.set_active(0)  # Domyślnie wybierz "Title" jako typ wyszukiwania
        # Dodaj rozwijalną listę dla wyboru wizualizacji
        self.visualization_type_combo = Gtk.ComboBoxText()
        self.visualization_type_combo.append_text("None")
        self.visualization_type_combo.append_text("Spectrum")
        self.visualization_type_combo.append_text("Waveform")
        self.visualization_type_combo.append_text("Points")
        self.visualization_type_combo.append_text("Tonal Transition")
        self.visualization_type_combo.set_active(0)  # Domyślnie wybierz "None"
        # Dodaj przycisk "Search"
        self.search_button = Gtk.Button(label="Search")
        self.search_button.connect("clicked", self.search_playlist)
        # Dodaj przycisk "Visualize"
        self.visualize_button = Gtk.Button(label="Visualize")
        self.visualize_button.connect("clicked", self.toggle_visualization)
        hbox_search = Gtk.HBox(homogeneous=False, spacing=0)
        hbox_search.pack_start(self.search_type_combo, False, False, 2)  # Dodaj rozwijalną listę
        hbox_search.pack_start(self.search_entry, True, True, 2)
        hbox_search.pack_start(self.search_button, False, False, 2)
        self.drawing_area = Gtk.DrawingArea()
        size = 200  # Stały rozmiar obszaru rysowania
        self.drawing_area.set_size_request(size, size)  # Ustaw rozmiar obszaru rysowania na stały rozmiar
        self.drawing_area.connect("draw", self.visualize)
        hbox_visualization = Gtk.HBox(homogeneous=False, spacing=0)
        hbox_visualization.pack_start(self.visualization_type_combo, False, False, 2)  # Dodaj rozwijalną listę
        hbox_visualization.pack_start(self.visualize_button, False, False, 2)

        vbox.pack_start(hbox_buttons, False, False, 2)
        vbox.pack_start(hbox_search, False, False, 2)  # Dodaj kontener z ComboBoxem i przyciskiem do głównego kontenera
        vbox.pack_start(hbox_visualization, False, False, 2)  # Dodaj kontener z ComboBoxem i przyciskiem do głównego kontenera
        # Add volume slider
        self.gain_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.gain_scale.set_digits(0)
        self.gain_scale.set_value_pos(Gtk.PositionType.BOTTOM)
        self.gain_scale.add_mark(0, Gtk.PositionType.BOTTOM, "0%")
        self.gain_scale.add_mark(50, Gtk.PositionType.BOTTOM, "50%")
        self.gain_scale.add_mark(100, Gtk.PositionType.BOTTOM, "100%")
        self.gain_scale.connect("value-changed", self.on_gain_scale_change)
        vbox.pack_start(self.gain_scale, False, False, 2)

        # Add position slider
        self.position_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        self.position_scale.set_digits(0)
        self.position_scale.set_value_pos(Gtk.PositionType.BOTTOM)
        self.position_scale.add_mark(10, Gtk.PositionType.BOTTOM, "10%")
        self.position_scale.add_mark(20, Gtk.PositionType.BOTTOM, "20%")
        self.position_scale.add_mark(30, Gtk.PositionType.BOTTOM, "30%")
        self.position_scale.add_mark(40, Gtk.PositionType.BOTTOM, "40%")
        self.position_scale.add_mark(50, Gtk.PositionType.BOTTOM, "50%")
        self.position_scale.add_mark(60, Gtk.PositionType.BOTTOM, "60%")
        self.position_scale.add_mark(70, Gtk.PositionType.BOTTOM, "70%")
        self.position_scale.add_mark(80, Gtk.PositionType.BOTTOM, "80%")
        self.position_scale.add_mark(90, Gtk.PositionType.BOTTOM, "90%")
        self.position_scale.add_mark(100, Gtk.PositionType.BOTTOM, "100%")
        self.position_scale.connect("value-changed", self.on_position_scale_change)
        vbox.pack_start(self.position_scale, False, False, 2)

        self.text_opacity = 1.0  # Początkowa przezroczystość tekstu
        self.font_options = cairo.FontOptions()
        self.font_options.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        self.font_options.set_hint_style(cairo.HINT_STYLE_FULL)
        self.font_options.set_hint_metrics(cairo.HINT_METRICS_ON)

        self.fft_data = None
        # Add the progress bar
        self.progress_bar = Gtk.ProgressBar()
        vbox.pack_start(self.progress_bar, False, False, 2)

        # Set the initial position of the slider to 0
        self.position_scale.set_value(0)
        vbox.pack_start(self.drawing_area, True, True, 2)
        self.window.show_all()



        self.playback_paused = False

        self.muted = False

        self.current_song_iter = False
        self.current_song_name = ""

        self.init_gst()
        self.init_audio_input()
        self.init_audio_output()
        
        self.update_time_timer = GLib.timeout_add(1000, self.update_time_label)
        self.update_progress_bar_timer = GLib.timeout_add(1000, self.update_progress_bar)  # Add progress bar update timer
  
        # Inicjalizacja PyAudio
        self.pa = pyaudio.PyAudio()
        self.stream_audio_input = None  # Strumień audio dla PyAudio
        self.stream_audio_output = None  # Strumień audio dla GStreamer
        # Inne inicjalizacje...
        self.visualizing = False  # Inicjalnie wizualizacja jest wyłączona

        self.repeat_mode = "off"
        self.repeat_one_enabled = False
        self.repeat_all_enabled = False

        self.pipeline = Gst.ElementFactory.make("playbin", "player")
        self.pipeline.set_property("volume", 0.25)  # Set default volume to 25%
        self.playback_paused = False

        self.muted = False
        self.muted_volume = 0.25  # Set initial muted volume to 25%

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

    def repeat_one(self):
        if self.repeat_mode == "one" and self.audio_buffer is None:
            # Pobierz aktualnie odtwarzany utwór
            selection = self.playlist_view.get_selection()
            model, selected_song_iter = selection.get_selected()
            if selected_song_iter:
                self.pipeline.set_state(Gst.State.PLAYING)  # Kontynuuj odtwarzanie
            return True
        elif self.repeat_mode == "one" and self.pipeline.get_state(0)[1] == Gst.State.NULL:
            self.play_audio_file(self.current_song_name)
            return True
        return False

        self.update_now_playing_label_timeout = GLib.timeout_add(100, self.update_now_playing_label)
        self.update_next_playing_label_timeout = GLib.timeout_add(100, self.update_next_playing_label)
        self.update_previous_playing_label_timeout = GLib.timeout_add(100, self.update_previous_playing_label)

    def repeat_all(self):
        if self.repeat_mode == "all" and self.audio_buffer is None:
            # Pobierz aktualnie odtwarzany utwór
            selection = self.playlist_view.get_selection()
            model, selected_song_iter = selection.get_selected()
            if selected_song_iter:
                # Pobierz następny utwór na liście
                next_song_iter = self.playlist_store.iter_next(selected_song_iter)
                if not next_song_iter:
                    # Jeśli nie ma następnego utworu, przejdź na początek listy
                    next_song_iter = self.playlist_store.get_iter_first()
                if next_song_iter:
                    next_song_name = self.playlist_store.get_value(next_song_iter, 0)
                    self.play_audio_file(next_song_name)
            return True
        elif self.repeat_mode == "all" and self.pipeline.get_state(0)[1] == Gst.State.NULL:
            # Pobierz aktualnie odtwarzany utwór
            selection = self.playlist_view.get_selection()
            model, selected_song_iter = selection.get_selected()
            if selected_song_iter:
                # Pobierz następny utwór na liście
                next_song_iter = self.playlist_store.iter_next(selected_song_iter)
                if not next_song_iter:
                    # Jeśli nie ma następnego utworu, przejdź na początek listy
                    next_song_iter = self.playlist_store.get_iter_first()
                if next_song_iter:
                    next_song_name = self.playlist_store.get_value(next_song_iter, 0)
                    self.play_audio_file(next_song_name)
            return True
        return False

        self.update_now_playing_label_timeout = GLib.timeout_add(100, self.update_now_playing_label)
        self.update_next_playing_label_timeout = GLib.timeout_add(100, self.update_next_playing_label)
        self.update_previous_playing_label_timeout = GLib.timeout_add(100, self.update_previous_playing_label)

    def toggle_repeat_mode(self, widget, mode):
        self.repeat_mode = mode
        if mode == "one":
            self.repeat_one_enabled = True
            self.repeat_all_enabled = False
        elif mode == "all":
            self.repeat_one_enabled = False
            self.repeat_all_enabled = True
        else:
            self.repeat_one_enabled = False
            self.repeat_all_enabled = False

    def toggle_visualization(self, widget):
        self.visualizing = not self.visualizing  # Zmień stan wizualizacji (włącz/wyłącz)
        self.visualize_button.set_label("Stop Visualization" if self.visualizing else "Visualize")


    def on_playlist_view_row_activated(self, view, path, column):
        model = view.get_model()
        song_path = model[path][0]
        self.play_audio_file(song_path)
        self.current_song_iter = model.get_iter(path)
        self.update_now_playing_label_timeout = GLib.timeout_add(100, self.update_now_playing_label)
        self.update_next_playing_label_timeout = GLib.timeout_add(100, self.update_next_playing_label)
        self.update_previous_playing_label_timeout = GLib.timeout_add(100, self.update_previous_playing_label)

    def play_next_track(self, widget):
        next_song_iter = self.get_next_song_iter()
        if next_song_iter:
            next_song_path = self.playlist_store.get_value(next_song_iter, 0)
            self.play_audio_file(next_song_path)
            self.current_song_iter = next_song_iter
            self.update_now_playing_label_timeout = GLib.timeout_add(100, self.update_now_playing_label)
            self.update_next_playing_label_timeout = GLib.timeout_add(100, self.update_next_playing_label)
            self.update_previous_playing_label_timeout = GLib.timeout_add(100, self.update_previous_playing_label)
            # Przekazujemy ścieżkę do pliku audio do funkcji extract_and_display_album_cover
            self.extract_and_display_album_cover(next_song_path)


    def play_previous_track(self, widget):
        previous_song_iter = self.get_previous_song_iter()
        if previous_song_iter:
            previous_song_path = self.playlist_store.get_value(previous_song_iter, 0)
            self.play_audio_file(previous_song_path)
            self.current_song_iter = previous_song_iter
            self.update_next_playing_label_timeout = GLib.timeout_add(100, self.update_next_playing_label)
            self.update_now_playing_label_timeout = GLib.timeout_add(100, self.update_now_playing_label)
            self.update_previous_playing_label_timeout = GLib.timeout_add(100, self.update_previous_playing_label)
            # Przekazujemy ścieżkę do pliku audio do funkcji extract_and_display_album_cover
            self.extract_and_display_album_cover(previous_song_path)


    def visualize(self, widget, cr):
        if self.visualizing:
            selected_text = self.visualization_type_combo.get_active_text()
            if selected_text == "none":
                self.draw_0(widget, cr)
            if selected_text == "Spectrum":
                self.draw_1(widget, cr)
            elif selected_text == "Waveform":
                self.draw_2(widget, cr)
            elif selected_text == "Points":
                self.draw_3(widget, cr)
            elif selected_text == "Tonal Transition":
                self.draw_4(widget, cr)
            else:
                # Obsługa innych opcji wizualizacji
                pass

    def get_current_song_iter(self):
        if self.current_song_iter:
            current_iter = self.current_song_iter
            if current_iter is not None:
                return current_iter
            else:
                return self.playlist_store.get_iter_current()
        else:
            return self.playlist_store.get_iter_first()

    def get_next_song_iter(self):
        if self.current_song_iter:
            current_iter = self.current_song_iter
            next_iter = self.playlist_store.iter_next(current_iter)
            if next_iter is not None:
                return next_iter
            else:
                return self.playlist_store.get_iter_first()
        else:
            return self.playlist_store.get_iter_first()

    def get_previous_song_iter(self):
        if self.current_song_iter:
            current_iter = self.current_song_iter
            previous_iter = self.playlist_store.iter_previous(current_iter)
            if previous_iter is not None:
                return previous_iter
            else:
                return self.playlist_store.get_iter_first()
        else:
            return self.playlist_store.get_iter_first()


    def play(self, widget):
        selection = self.playlist_view.get_selection()
        model, selected_song_iter = selection.get_selected()

        if selected_song_iter:
            song_path = model.get_value(selected_song_iter, 0)
            self.play_audio_file(song_path)

            GLib.timeout_add(100, self.update_bars)
            self.update_next_playing_label_timeout = GLib.timeout_add(100, self.update_next_playing_label)
            self.update_now_playing_label_timeout = GLib.timeout_add(100, self.update_now_playing_label)
            self.update_previous_playing_label_timeout = GLib.timeout_add(100, self.update_previous_playing_label)
            self.extract_and_display_album_cover(song_path)

    def buffer_audio_data(self, file_path):
        try:
            encoded_file_path = quote(file_path)
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.set_property("uri", f"file://{encoded_file_path}")
            self.pipeline.set_state(Gst.State.PAUSED)
            self.playback_paused = True

            # Pobieraj dane audio i zapisuj je w buforze przez określony czas
            self.audio_buffer = bytearray()
            start_time = time.time()

            while time.time() - start_time < self.buffer_duration:
                audio_data = self.read_audio_data()
                self.audio_buffer.extend(audio_data.tobytes())

            self.buffer_ready = True  # Ustawiamy buffer_ready na True, gdy bufor jest gotowy
            self.current_song_name = os.path.basename(file_path)  # Przechowujemy nazwę aktualnej piosenki
        except Exception as e:
            print(f"Error while buffering audio data: {e}")

    def buffer_audio_file(self, file_path):
        try:
            encoded_file_path = quote(file_path)
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.set_property("uri", f"file://{encoded_file_path}")
            self.pipeline.set_state(Gst.State.PAUSED)
            self.playback_paused = True

            # Pobieraj dane audio i zapisuj je w buforze przez określony czas
            self.audio_buffer = bytearray()
            start_time = time.time()

            while time.time() - start_time < self.buffer_duration:
                audio_data = self.read_audio_data()
                self.audio_buffer.extend(audio_data.tobytes())

            self.buffer_ready = True  # Ustawiamy buffer_ready na True, gdy bufor jest gotowy
            self.current_song_name = os.path.basename(file_path)  # Przechowujemy nazwę aktualnej piosenki
        except Exception as e:
            print(f"Error while buffering audio file: {e}")


    def extract_and_display_album_cover(self, audio_file):
        # Otwórz plik audio
        audio = eyed3.load(audio_file)

        # Sprawdź, czy plik audio zawiera metadane i okładkę albumu
        if audio.tag and audio.tag.images:
            # Wybierz pierwszą okładkę albumu
            album_art = audio.tag.images[0].image_data

            # Utwórz obiekt GdkPixbuf na podstawie danych obrazu
            loader = GdkPixbuf.PixbufLoader()
            loader.write(album_art)
            loader.close()
            pixbuf = loader.get_pixbuf()

            # Przeskaluj okładkę albumu do rozmiaru obszaru okładki
            scaled_pixbuf = self.scale_album_cover(pixbuf, self.album_cover_fixed.get_allocation().width, self.album_cover_fixed.get_allocation().height)

            # Wyświetl przeskalowaną okładkę
            self.display_album_cover(scaled_pixbuf)
        else:
            # Jeśli nie ma okładki albumu, wyświetl placeholder
            self.display_album_cover_placeholder()

    def scale_album_cover(self, pixbuf, target_width, target_height):
        # Pobierz oryginalny rozmiar okładki albumu
        orig_width = pixbuf.get_width()
        orig_height = pixbuf.get_height()

        # Oblicz stosunek skalowania dla szerokości i wysokości
        width_ratio = target_width / orig_width
        height_ratio = target_height / orig_height

        # Wybierz mniejszy stosunek skalowania, aby zachować proporcje
        scale_ratio = min(width_ratio, height_ratio)

        # Oblicz nowe wymiary na podstawie proporcji
        new_width = int(orig_width * scale_ratio)
        new_height = int(orig_height * scale_ratio)

        # Przeskaluj okładkę albumu
        scaled_pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)

        return scaled_pixbuf

    def display_album_cover(self, pixbuf):
        # Usuń istniejące elementy z obszaru okładki albumu
        for child in self.album_cover_fixed.get_children():
            self.album_cover_fixed.remove(child)

        # Utwórz widżet Gtk.Image z przeskalowaną okładką albumu
        image = Gtk.Image()
        image.set_from_pixbuf(pixbuf)

        # Dodaj przeskalowaną okładkę albumu do obszaru okładki
        self.album_cover_fixed.add(image)
        self.album_cover_fixed.show_all()

    def display_album_cover_placeholder(self):
        # Usuń istniejące elementy z obszaru okładki albumu
        for child in self.album_cover_fixed.get_children():
            self.album_cover_fixed.remove(child)

        # Utwórz widżet Gtk.Image z domyślną ikoną brakującego obrazu
        image = Gtk.Image()
        image = Gtk.Image.new_from_icon_name("image-missing", Gtk.IconSize.LARGE_TOOLBAR)

        # Dodaj ikonę brakującego obrazu do obszaru okładki
        self.album_cover_fixed.add(image)
        self.album_cover_fixed.show_all()

    def draw_0(self, widget, cr):
        pass

    def draw_1(self, widget, cr):
        if self.fft_data is not None:
            cr.set_source_rgb(0, 0, 0)
            cr.paint()

            num_bars = 64 # Liczba słupków
            bar_width = widget.get_allocated_width() / num_bars
            max_amplitude = np.max(self.fft_data)

            for i in range(num_bars):
                start = int((i / num_bars) * len(self.fft_data))
                end = int(((i + 1) / num_bars) * len(self.fft_data))
                bar_height = np.max(self.fft_data[start:end])
                if max_amplitude != 0:
                    bar_height /= max_amplitude  # Normalizacja do zakresu 0-1
                else:
                    bar_height = 0  # Jeśli max_amplitude == 0, ustaw bar_height na 0

                new_bar_height = bar_height
                # Generuj losowy kolor dla każdego słupka
                color = np.random.rand(3)
                transparency = 0.5 + (bar_height * 0.5)  # Od 50% do 100%
                #color = (0, 0, 0)
                
                self.draw_bar(cr, i * bar_width, (1 - new_bar_height) * widget.get_allocated_height(), bar_width, new_bar_height * widget.get_allocated_height(), color, transparency)

                # Dodaj sinusoidalny waveform
                #self.draw_waveform(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color)
                #self.draw_points(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color, transparency)
                # Rysuj przejście tonalne
                #self.draw_tonal_transition(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color, transparency)
                # Oblicz ilość punktów
                num_points = int(bar_height * 10)  # Przykładowa liczba punktów
                num_points = max(num_points, 1)  # Minimalnie jeden punkt

                # Rysuj punkty w górę z przejściami
                #self.draw_points_with_transitions(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color, transparency, num_points)

    def draw_2(self, widget, cr):
        if self.fft_data is not None:
            cr.set_source_rgb(0, 0, 0)
            cr.paint()

            num_bars = 64 # Liczba słupków
            bar_width = widget.get_allocated_width() / num_bars
            max_amplitude = np.max(self.fft_data)

            for i in range(num_bars):
                start = int((i / num_bars) * len(self.fft_data))
                end = int(((i + 1) / num_bars) * len(self.fft_data))
                bar_height = np.max(self.fft_data[start:end])
                if max_amplitude != 0:
                    bar_height /= max_amplitude  # Normalizacja do zakresu 0-1
                else:
                    bar_height = 0  # Jeśli max_amplitude == 0, ustaw bar_height na 0

                new_bar_height = bar_height
                # Generuj losowy kolor dla każdego słupka
                color = np.random.rand(3)
                transparency = 0.5 + (bar_height * 0.5)  # Od 50% do 100%
                #color = (0, 0, 0)
                
                #self.draw_bar(cr, i * bar_width, (1 - new_bar_height) * widget.get_allocated_height(), bar_width, new_bar_height * widget.get_allocated_height(), color, transparency)

                # Dodaj sinusoidalny waveform
                #self.draw_waveform(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color)
                self.draw_points(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color, transparency)
                # Rysuj przejście tonalne
                #self.draw_tonal_transition(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color, transparency)
                # Oblicz ilość punktów
                num_points = int(bar_height * 10)  # Przykładowa liczba punktów
                num_points = max(num_points, 1)  # Minimalnie jeden punkt

                # Rysuj punkty w górę z przejściami
                #self.draw_points_with_transitions(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color, transparency, num_points)

    def draw_3(self, widget, cr):
        if self.fft_data is not None:
            cr.set_source_rgb(0, 0, 0)
            cr.paint()

            num_bars = 64 # Liczba słupków
            bar_width = widget.get_allocated_width() / num_bars
            max_amplitude = np.max(self.fft_data)

            for i in range(num_bars):
                start = int((i / num_bars) * len(self.fft_data))
                end = int(((i + 1) / num_bars) * len(self.fft_data))
                bar_height = np.max(self.fft_data[start:end])
                if max_amplitude != 0:
                    bar_height /= max_amplitude  # Normalizacja do zakresu 0-1
                else:
                    bar_height = 0  # Jeśli max_amplitude == 0, ustaw bar_height na 0

                new_bar_height = bar_height
                # Generuj losowy kolor dla każdego słupka
                color = np.random.rand(3)
                transparency = 0.5 + (bar_height * 0.5)  # Od 50% do 100%
                #color = (0, 0, 0)
                
                #self.draw_bar(cr, i * bar_width, (1 - new_bar_height) * widget.get_allocated_height(), bar_width, new_bar_height * widget.get_allocated_height(), color, transparency)

                # Dodaj sinusoidalny waveform
                #self.draw_waveform(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color)
                #self.draw_points(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color, transparency)
                # Rysuj przejście tonalne
                self.draw_tonal_transition(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color, transparency)
                # Oblicz ilość punktów
                num_points = int(bar_height * 10)  # Przykładowa liczba punktów
                num_points = max(num_points, 1)  # Minimalnie jeden punkt

                # Rysuj punkty w górę z przejściami
                #self.draw_points_with_transitions(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color, transparency, num_points)

    def draw_4(self, widget, cr):
        if self.fft_data is not None:
            cr.set_source_rgb(0, 0, 0)
            cr.paint()

            num_bars = 64 # Liczba słupków
            bar_width = widget.get_allocated_width() / num_bars
            max_amplitude = np.max(self.fft_data)

            for i in range(num_bars):
                start = int((i / num_bars) * len(self.fft_data))
                end = int(((i + 1) / num_bars) * len(self.fft_data))
                bar_height = np.max(self.fft_data[start:end])
                if max_amplitude != 0:
                    bar_height /= max_amplitude  # Normalizacja do zakresu 0-1
                else:
                    bar_height = 0  # Jeśli max_amplitude == 0, ustaw bar_height na 0

                new_bar_height = bar_height
                # Generuj losowy kolor dla każdego słupka
                color = np.random.rand(3)
                transparency = 0.5 + (bar_height * 0.5)  # Od 50% do 100%
                #color = (0, 0, 0)
                
                #self.draw_bar(cr, i * bar_width, (1 - new_bar_height) * widget.get_allocated_height(), bar_width, new_bar_height * widget.get_allocated_height(), color, transparency)

                # Dodaj sinusoidalny waveform
                #self.draw_waveform(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color)
                #self.draw_points(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color, transparency)
                # Rysuj przejście tonalne
                #self.draw_tonal_transition(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color, transparency)
                # Oblicz ilość punktów
                num_points = int(bar_height * 10)  # Przykładowa liczba punktów
                num_points = max(num_points, 1)  # Minimalnie jeden punkt

                # Rysuj punkty w górę z przejściami
                self.draw_points_with_transitions(cr, i * bar_width, (1 - bar_height) * widget.get_allocated_height(), bar_width, bar_height * widget.get_allocated_height(), color, transparency, num_points)

    def update_spectrum(self):
        # Symulacja danych FFT (wymaga prawdziwego źródła danych FFT)
        self.fft_data = np.random.rand(64)

        # Pulsowanie tekstu
        self.text_opacity -= 0.05  # Zmniejszenie przezroczystości
        if self.text_opacity < 0:
            self.text_opacity = 1.0  # Po zaniknięciu tekstu, przywróć pełną przezroczystość

        self.drawing_area.queue_draw()
        return True


    def draw_points_with_transitions(self, cr, x, y, width, height, color, transparency, num_points):
        red, green, blue = color

        step = width / num_points / 4

        for i in range(num_points):
            x1 = x #+ i * step
            y1 = y + height * i / num_points
            size = 5.0  # Rozmiar punktu

            # Ustal przejście między punktami
            transition = i / num_points  # Od 0 do 1

            # Ustaw kolor punktu z określoną przezroczystością
            cr.set_source_rgba(red, green, blue, transition * transparency)
            cr.arc(x1, y1, size, 0, 2 * np.pi)
            cr.fill()

    def draw_tonal_transition(self, cr, x, y, width, height, color, transparency):
        red, green, blue = color

        num_points = int(width)
        step = width / num_points

        cr.set_line_width(2.0)

        for i in range(num_points):
            x1 = x + i * step
            x2 = x + (i + 1) * step
            gradient_color = (
                red - red * i / num_points,
                green - green * i / num_points,
                blue - blue * i / num_points
            )
            transparency = 0.5 + (height * i / num_points * 0.5)  # Przejście tonalne w oparciu o wysokość

            # Rysuj linię z gradientem kolorów
            cr.set_source_rgba(gradient_color[0], gradient_color[1], gradient_color[2], transparency)
            cr.move_to(x1, y)
            cr.line_to(x2, y)
            cr.line_to(x2, y - height)
            cr.line_to(x1, y - height)
            cr.close_path()
            cr.fill()

    def draw_points(self, cr, x, y, width, height, color, transparency):
        red, green, blue = color

        num_points = int(width)
        step = width / num_points

        for i in range(num_points):
            x1 = x #+ i * step
            y1 = y + height * i / num_points
            size = 5.0  # Rozmiar punktu

            # Interpolacja kolorów pomiędzy sąsiednimi punktami
            if i < num_points - 1:
                x2 = x + (i + 1) * step
                y2 = y + height * (i + 1) / num_points
                gradient = np.linspace(0, 1, num_points)
                red_i = int((1 - gradient[i]) * red + gradient[i] * red)
                green_i = int((1 - gradient[i]) * green + gradient[i] * green)
                blue_i = int((1 - gradient[i]) * blue + gradient[i] * blue)
                cr.set_source_rgba(red_i / 255, green_i / 255, blue_i / 255, transparency)
            else:
                cr.set_source_rgba(red, green, blue, transparency)

            # Rysuj punkt jako okrągły
            cr.arc(x1, y1, size, 0, 2 * np.pi)
            cr.fill()

    def draw_bar(self, cr, x, y, width, height, color, transparency):
        red, green, blue = color

        # Ustaw kolor słupka z określoną przezroczystością
        cr.set_source_rgba(red, green, blue, transparency)
        cr.rectangle(x, y, width / 2, height)
        cr.fill()

        # Ustaw kolor obramowania słupka na pełną nieprzezroczystość
        cr.set_source_rgb(0, 0, 0)

    def draw_waveform(self, cr, x, y, width, height, color):
        red, green, blue = color

        num_points = int(width)
        step = width / num_points

        cr.set_source_rgb(red, green, blue)
        cr.set_line_width(2.0)

        for i in range(num_points):
            x1 = x + i * step
            y1 = y + height / 2 * np.sin(2 * np.pi * i / num_points)
            x2 = x + (i + 1) * step
            y2 = y + height / 2 * np.sin(2 * np.pi * (i + 1) / num_points)

            cr.move_to(x1, y1)
            cr.line_to(x2, y2)

        cr.stroke()


    def update_bars(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            query = Gst.Query.new_seeking(Gst.Format.TIME)
            if self.pipeline.query(query):
                _, position = self.pipeline.query_position(Gst.Format.TIME)
                _, duration = self.pipeline.query_duration(Gst.Format.TIME)
                progress = float(position) / float(duration) if duration > 0 else 0.0
                
                # Odczytaj dane audio z mikrofonu
                audio_data = self.read_audio_data()
                
                # Oblicz FFT na podstawie danych audio
                num_samples = 64  # Przykładowa liczba próbek
                fft_data = np.fft.fft(audio_data)
                fft_data = np.abs(fft_data[:num_samples])  # Pobierz amplitudy tylko pierwszych próbek
                
                self.fft_data = fft_data * progress
                GLib.idle_add(self.drawing_area.queue_draw)
        return True


    def init_gst(self):
        self.pipeline = Gst.Pipeline()

        source = Gst.ElementFactory.make("uridecodebin", "source")
        audioconvert = Gst.ElementFactory.make("audioconvert", "audioconvert")
        audioresample = Gst.ElementFactory.make("audioresample", "audioresample")
        sink = Gst.ElementFactory.make("autoaudiosink", "sink")

        if not source or not audioconvert or not audioresample or not sink:
            print("One or more elements could not be created. Exiting.")
            exit(1)

        self.pipeline.add(source)
        self.pipeline.add(audioconvert)
        self.pipeline.add(audioresample)
        self.pipeline.add(sink)

        source.link(audioconvert)
        audioconvert.link(audioresample)
        audioresample.link(sink)

        source.connect("pad-added", self.on_pad_added)

    def on_pad_added(self, element, pad):
        sink_pad = Gst.Element.get_static_pad(element, "sink")
        if not sink_pad.is_linked():
            pad.link(sink_pad)

    def init_audio_input(self):
        # Konfiguracja strumienia audio
        self.stream_audio_input = self.pa.open(
            format=pyaudio.paInt16,
            channels=2,  # Stereo
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )

    def init_audio_output(self):
        # Konfiguracja strumienia audio
        self.stream_audio_output = self.pa.open(
            format=self.pa.get_format_from_width(self.sample_width),
            channels=self.num_channels,
            rate=self.sample_rate,
            output=True
        )

    def read_audio_data(self):
        if self.stream_audio_input is None:
            # Konfiguracja strumienia audio
            sample_rate = 44100  # Przykładowa częstotliwość próbkowania
            audio_format = pyaudio.paInt16

            self.stream_audio_input = self.pa.open(
                format=audio_format,
                channels=2,  # Mono
                rate=sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size  # Używamy chunk_size jako rozmiar paczki
            )

        try:
            audio_data = self.stream_audio_input.read(self.chunk_size)  # Używamy self.chunk_size
            audio_data = np.frombuffer(audio_data, dtype=np.int16)
            return audio_data
        except IOError as e:
            print("Błąd odczytu danych audio:", e)
            return np.zeros(self.chunk_size, dtype=np.int16)

    def play_audio_file(self, file_path):
        try:
            encoded_file_path = quote(file_path)
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.set_property("uri", f"file://{encoded_file_path}")
            self.pipeline.set_state(Gst.State.PLAYING)
            self.playback_paused = False
        except Exception as e:
            print(f"Error while playing audio: {e}")



    def toggle_pause(self, widget):
        if self.playback_paused:
            self.pipeline.set_state(Gst.State.PLAYING)
            self.playback_paused = False
        else:
            self.pipeline.set_state(Gst.State.PAUSED)
            self.playback_paused = True

    def stop(self, widget):
        self.pipeline.set_state(Gst.State.NULL)

    def on_gain_scale_change(self, widget):
        value = self.gain_scale.get_value()
        volume = value / 100  # Przelicz wartość z zakresu 0-100 na zakres 0-1
        self.pipeline.set_property("volume", volume)

    def on_position_scale_change(self, widget):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            value = self.position_scale.get_value()
            position = (value / 100) * self.pipeline.query_duration(Gst.Format.TIME)[1]
            self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, position)
            self.pipeline.set_state(Gst.State.PLAYING)  # Rozpocznij ponowne odtwarzanie


    def update_position_slider(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            position, duration = self.pipeline.query_position(Gst.Format.TIME)[1], self.pipeline.query_duration(Gst.Format.TIME)[1]
            value = (position / duration) * 100
            self.position_scale.set_value(value)
        return True

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)
        elif t == Gst.MessageType.EOS:
            if self.repeat_mode == "one":
                # Powtórz aktualny utwór, przewijając do początku
                self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
                self.pipeline.set_state(Gst.State.PLAYING)  # Rozpocznij ponowne odtwarzanie
            elif self.repeat_mode == "all":
                selection = self.playlist_view.get_selection()
                model, selected_song_iter = selection.get_selected()
                if selected_song_iter:
                    next_song_iter = model.iter_next(selected_song_iter)
                    if not next_song_iter:
                        # Jeśli to koniec playlisty, zacznij od początku
                        next_song_iter = model.get_iter_first()
                    if next_song_iter:
                        next_song_path = model.get_value(next_song_iter, 0)
                        self.play_audio_file(next_song_path)
            else:
                self.pipeline.set_state(Gst.State.NULL)
                print("End-Of-Stream reached")

        # Obsługa zdarzenia zmiany utworu
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                if new_state == Gst.State.PLAYING:
                    self.update_now_playing_label()
                    self.update_progress_bar()  # Rozpocznij aktualizację paska postępu



    def update_previous_playing_label(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            previous_song_iter = self.get_previous_song_iter()
            if previous_song_iter:
                title = self.playlist_store.get_value(previous_song_iter, 4)
                artist = self.playlist_store.get_value(previous_song_iter, 1)
                print(f"Updating Previous Playing label with artist: {artist}, title: {title}")
                self.previous_playing_label.set_markup(
                    f'<span font_desc="12">Previous Track:</span> {artist} - {title}')
            else:
                self.previous_playing_label.set_markup("")

    def update_next_playing_label(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            next_song_iter = self.get_next_song_iter()
            if next_song_iter:
                title = self.playlist_store.get_value(next_song_iter, 4)
                artist = self.playlist_store.get_value(next_song_iter, 1)
                print(f"Updating Next Playing label with artist: {artist}, title: {title}")
                self.next_playing_label.set_markup(
                    f'<span font_desc="12">Next Up:</span> {artist} - {title}')
            else:
                self.next_playing_label.set_markup("")

    def update_now_playing_label(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            current_song_iter = self.get_current_song_iter()
            if current_song_iter:
                title = self.playlist_store.get_value(current_song_iter, 4)
                artist = self.playlist_store.get_value(current_song_iter, 1)
                print(f"Updating Now Playing label with artist: {artist}, title: {title}")
                self.now_playing_label.set_markup(
                    f'<span font_desc="12">Now Up:</span> {artist} - {title}')
            else:
                self.now_playing_label.set_markup("")

    def update_time_label(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            position, duration = self.pipeline.query_position(Gst.Format.TIME)[1], self.pipeline.query_duration(Gst.Format.TIME)[1]
            position_sec = position / Gst.SECOND
            duration_sec = duration / Gst.SECOND
            time_str = "{:02}:{:02}:{:02} / {:02}:{:02}:{:02}".format(
                int(position_sec // 3600),
                int((position_sec // 60) % 60),
                int(position_sec % 60),
                int(duration_sec // 3600),
                int((duration_sec // 60) % 60),
                int(duration_sec % 60),
            )
            self.time_label.set_text(time_str)
        return True

    def update_progress_bar(self):
        if self.pipeline.get_state(0)[1] == Gst.State.PLAYING:
            position, duration = self.pipeline.query_position(Gst.Format.TIME)[1], self.pipeline.query_duration(Gst.Format.TIME)[1]
            fraction = float(position) / float(duration)
            self.progress_bar.set_fraction(fraction)
        return True

    def load_from_dir(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a directory",
            parent=self.window,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )

        # Dodaj przyciski
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder_path = dialog.get_filename()
            self.load_music_from_folder(folder_path)
        dialog.destroy()

    def load_music_from_folder(self, folder_path):
        if folder_path:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith(('.mp3', '.wav', '.flac')):
                        file_path = os.path.join(root, file)
                        self.append_song_to_playlist(file_path)

    def append_from_file(self, widget):
        dialog = Gtk.FileChooserDialog("Please choose a file", self.window, Gtk.FileChooserAction.OPEN,
                                       ("Cancel", Gtk.ResponseType.CANCEL, "Open", Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_current_folder(os.path.expanduser("~"))

        filter_mp3 = Gtk.FileFilter()
        filter_mp3.set_name("MP3 files")
        filter_mp3.add_mime_type("audio/mpeg")
        dialog.add_filter(filter_mp3)

        filter_wav = Gtk.FileFilter()
        filter_wav.set_name("WAV files")
        filter_wav.add_mime_type("audio/wav")
        dialog.add_filter(filter_wav)

        filter_flac = Gtk.FileFilter()
        filter_flac.set_name("FLAC files")
        filter_flac.add_mime_type("audio/flac")
        dialog.add_filter(filter_flac)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            self.append_song_to_playlist(file_path)
        dialog.destroy()

    def append_song_to_playlist(self, file_path):
        audiofile = eyed3.load(file_path)
        title = audiofile.tag.title if audiofile.tag.title else os.path.basename(file_path)
        artist = audiofile.tag.artist if audiofile.tag.artist else "Unknown Artist"
        genre = str(audiofile.tag.genre) if audiofile.tag.genre else "Unknown Genre"
        album = audiofile.tag.album if audiofile.tag.album else "Unknown Album"
        filename = os.path.basename(file_path)

        self.playlist_store.append([file_path, artist, genre, album, title])
        self.original_playlist.append([file_path, artist, genre, album, title])

    def clear_playlist(self, widget):
        self.playlist_store.clear()
        self.original_playlist.clear()

    def shuffle_playlist(self, widget):
        random.shuffle(self.original_playlist)
        self.playlist_store.clear()
        for song in self.original_playlist:
            self.playlist_store.append(song)

    def save_playlist(self, widget):
        dialog = Gtk.FileChooserDialog("Save Playlist", self.window, Gtk.FileChooserAction.SAVE,
                                       ("Cancel", Gtk.ResponseType.CANCEL, "Save", Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_current_folder(os.path.expanduser("~"))
        dialog.set_current_name("playlist.txt")

        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            self.save_playlist_to_file(file_path)
        dialog.destroy()

    def save_playlist_to_file(self, file_path):
        with open(file_path, 'w') as f:
            for song in self.original_playlist:
                f.write(f"{song[0]}\n")

    def load_playlist(self, widget):
        dialog = Gtk.FileChooserDialog("Open Playlist", self.window, Gtk.FileChooserAction.OPEN,
                                       ("Cancel", Gtk.ResponseType.CANCEL, "Open", Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_current_folder(os.path.expanduser("~"))

        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            self.load_playlist_from_file(file_path)
        dialog.destroy()

    def load_playlist_from_file(self, file_path):
        with open(file_path, 'r') as f:
            lines = f.read().splitlines()
            for line in lines:
                self.append_song_to_playlist(line)


    def toggle_mute(self, widget):
        if self.muted:
            # Restore the previous volume
            self.pipeline.set_property("volume", self.gain_scale.get_value() / 100)
        else:
            # Mute by setting the volume to 0
            self.pipeline.set_property("volume", 0)
        self.muted = not self.muted

    def search_playlist(self, widget):
        search_text = self.search_entry.get_text()
        search_type = self.search_type_combo.get_active_text()
        self.filter_playlist(search_text, search_type)

    def filter_playlist(self, search_text, search_type):
        self.playlist_store.clear()
        for song in self.original_playlist:
            if search_type == "Title" and search_text.lower() in song[4].lower():
                self.playlist_store.append(song)
            elif search_type == "Artist" and search_text.lower() in song[1].lower():
                self.playlist_store.append(song)
            elif search_type == "Genre" and search_text.lower() in song[2].lower():
                self.playlist_store.append(song)
            elif search_type == "Album" and search_text.lower() in song[3].lower():
                self.playlist_store.append(song)

if __name__ == "__main__":
    player = MusicPlayer()
    Gtk.main()

