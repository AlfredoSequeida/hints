import Gio from "gi://Gio";
import { Extension } from "resource:///org/gnome/shell/extensions/extension.js";
const { Gdk, Meta, Atspi } = imports.gi;

export default class HintsExtension extends Extension {
  constructor(metadata) {
    super(metadata);
    this._ownership = null;
    const f = Gio.File.new_for_path(`${this.path}/uk.co.realh.Hints.xml`);
    const [_ok, contents, _etag] = f.load_contents(null);
    const decoder = new TextDecoder("utf-8");
    this.dbusSpec = decoder.decode(contents);
    this.hintsService = new Hints();
    this.exportedObject = Gio.DBusExportedObject.wrapJSObject(
      this.dbusSpec,
      this.hintsService,
    );
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
      this.exportedObject.unexport();
      Gio.bus_unown_name(this._ownership);
      this._ownership = null;
    }
  }

  onBusAcquired(connection, _name) {
    this.exportedObject.export(connection, "/uk/co/realh/Hints");
  }

  onNameAcquired(_connection, _name) {}

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
      console.log("uk.co.realh.Hints: no window focused");
      return [0, 0, 0, 0, -1, "", -1];
    }

    const pid = w.get_pid();

    const desktop = Atspi.get_desktop(0);
    let toolkit_name = "";
    let toolkit_version = "";

    for (
      let app_index = 0;
      app_index < desktop.get_child_count();
      app_index++
    ) {
      const current_window = desktop.get_child_at_index(app_index);
      if (current_window.get_process_id() == pid) {
        toolkit_name = current_window.get_toolkit_name();
        toolkit_version = current_window.get_toolkit_version();
        break;
      }
    }

    let x, y, width, height;

    /* GTK 4 decorations behave differently that other toolkits in Mutter;
     * resulting in unexpected hint offsets. To resolve alignment issues,
     * we use get_frame_rect() for GTK 4 applications and get_buffer_rect() for
     * everything else.
     */
    if (toolkit_name == "GTK" && +toolkit_version.split(".", 1) >= 4) {
      const rect = w.get_frame_rect();
      x = rect.x;
      y = rect.y;
      width = rect.width;
      height = rect.height;
    } else {
      const rect = w.get_buffer_rect();
      x = rect.x;
      y = rect.y;
      width = rect.width;
      height = rect.height;
    }

    const name = w.get_wm_class();
    const monitor = w.get_monitor();
    console.log(
      "uk.co.realh.Hints: FocusedWindowInfo => (" +
        `x=${x}, y=${y}, w=${width}, h=${height}, p=${pid}, ` +
        `name="${name}", monitor=${monitor})`,
    );
    return [x, y, width, height, pid, name, monitor];
  }

  // This is called before a window is shown. When a window matching pid
  // is shown, it will be set to the given position and monitor. The client
  // will typically create two windows, but both will have the same position
  // and monitor so we don't need to distinguish between them as long as
  // each one has its own handler.
  PositionWindow(x, y, monitor, pid) {
    let create_handler_id = null;
    let timeout_id = null;
    let configure_handler_id = null;

    console.log(
      `uk.co.realh.Hints: PositionWindow(x=${x}, y=${y}, ` +
        `monitor=${monitor}, pid=${pid})`,
    );

    const timeout_cb = () => {
      if (create_handler_id !== null) {
        console.log(
          "uk.co.realh.Hints: timeout waiting for window " + `from pid ${pid}`,
        );
        global.display.disconnect(create_handler_id);
        create_handler_id = null;
      }
      timeout_id = null;
    };

    const configure_cb = (window, config) => {
      console.log(
        "uk.co.realh.Hints: configure signal received, " +
          "moving to position ${x}, ${y}",
      );
      window.disconnect(configure_handler_id);
      // window.move_to_monitor(monitor);
      config.set_position(x, y);
    };

    const create_cb = (_display, window) => {
      if (window.get_pid() !== pid) {
        return;
      }

      console.log(`uk.co.realh.Hints: Matched window with pid ${pid}`);

      if (create_handler_id !== null) {
        global.display.disconnect(create_handler_id);
        create_handler_id = null;
      }
      if (timeout_id !== null) {
        clearTimeout(timeout_id);
        timeout_id = null;
      }

      configure_handler_id = window.connect("configure", configure_cb);
    };

    timeout_id = setTimeout(timeout_cb, 5000);
    create_handler_id = global.display.connect("window-created", create_cb);
  }
}
