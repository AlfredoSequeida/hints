import Gio from 'gi://Gio';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

export default class HintsExtension extends Extension {
    constructor() {
        this._ownership = null;
        const f = Gio.File.new_for_path(`${this.path}/uk.co.realh.Hints.xml`);
        const [contents, _] = f.load_contents(null);
        const decoder = new TextDecoder("utf-8");
        this.dbusSpec = decoder.decode(contents);
    }

    enable() {
        this._ownership = Gio.bus_own_name(
            Gio.BusType.SESSION,
            "uk.co.realh.Hints",
            Gio.BusNameOwnerFlags.NONE,
            this.onBusAcquired.bind(this),
            this.onNameAcquired.bind(this),
            this.onNameLost.bind(this),
        );
    }

    disable() {
        if (this._ownership) {
            Gio.bus_unown_name(this._ownership);
            this._ownership = null;
        }
    }

    onBusAcquired(_connection, _name) {
    }

    onNameAcquired(connection, _name) {
        const hintsService = new Hints();
        const exportedObject = Gio.DBusExportedObject.wrapJSObject(
            this.dbusSpec, hintsService);
        exportedObject.export(connection, "/uk/co/realh/Hints");
    }

    onNameLost(_connection, _name) {
        this._ownership = null;
    }
}

class Hints {
    // Returns [x, y, width, height, pid, name, monitor].
    // If no window is focused, returns [0, 0, 0, 0, -1, "", -1].
    // monitor is the index as returned by Meta.Window.get_monitor().
    FocusedWindowInfo() {
        const w = global.display.get_focus_window();
        if (!w) {
            return [0, 0, 0, 0, -1, "", -1];
        }
        const {x, y, width, height} = w.get_frame_rect();
        const pid = w.get_pid();
        const name = w.get_wm_class();
        const monitor = w.get_monitor();
        return [x, y, width, height, pid, name, monitor];
    }

    // This is called before a window is shown. When the window matching pid
    // and title is shown, it will be set to the given position and monitor.
    PositionWindow(x, y, monitor, pid, title) {
        let handler_id = null
        handler_id = global.display.connect("window-created",
            (_display, window) => {
                if (window.get_pid() !== pid || window.get_title() !== title) {
                    return
                }
                window.move(x, y);
                window.set_monitor(monitor);
                if (handler_id !== null) {
                    global.display.disconnect(handler_id);
                    handler_id = null;
                }
            }
        );
    }
}
