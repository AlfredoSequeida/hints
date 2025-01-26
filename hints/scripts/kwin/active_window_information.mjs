/* Get active window information using the Kwin API for plasma 6
 * @return Object with windown information for the current active window
 */
const getActiveWindowInformation = () => {
  const currentDesktop = workspace.currentDesktop;
  const clients = workspace.windowList();

  for (let i = 0; i < clients.length; i++) {
    const window = clients[i];
    if (window.active) {
      const geometry = window.clientGeometry;
      return {
        extents: [geometry.x, geometry.y, geometry.width, geometry.height],
        pid: window.pid,
        name: window.resourceClass,
      };
    }
  }
};

console.info(JSON.stringify(getActiveWindowInformation()));
