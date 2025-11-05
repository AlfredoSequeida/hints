import Gio from 'gi://Gio';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

// import St from 'gi://St';
// import Main from 'resource:///org/gnome/shell/ui/main.js';

export default class HintsExtension {
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
    // Returns [x, y, width, height, pid, name]
    // If no window is focused, returns [0, 0, 0, 0, -1, ""]
    FocusedWindowInfo() {
        const w = global.display.get_focus_window();
        if (!w) {
            return [0, 0, 0, 0, -1, ""];
        }
        const {x, y, width, height} = w.get_frame_rect();
        const pid = w.get_pid();
        const name = w.get_wm_class();
        return [x, y, width, height, pid, name];
    }
}
