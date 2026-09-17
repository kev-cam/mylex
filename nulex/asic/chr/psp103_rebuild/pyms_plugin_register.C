// Wrapper: export the standard Xyce plugin entry point registerOpenDevices,
// which `Xyce -plugin` dlsym's — the PyMS-generated device only provides the
// namespaced PYMS_PSP103VA::registerDevice + a load constructor (which -plugin
// does not invoke). This forwards the -plugin call to the device registration.
#include "N_DEV_PYMS_PSP103VA.h"
#include <set>
namespace Xyce { namespace Device {
  void registerOpenDevices(const DeviceCountMap &deviceMap,
                           const std::set<int> &levelSet, bool /*loadPlugins*/) {
    PYMS_PSP103VA::registerDevice(deviceMap, levelSet);
  }
} }
