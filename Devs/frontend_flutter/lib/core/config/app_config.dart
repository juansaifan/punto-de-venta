/// Configuración de la aplicación POS.
///
/// En el modo mock/offline, el valor no se usa para llamadas reales.
class ConfiguracionAplicacion {
  ConfiguracionAplicacion._();

  static const BackendEntorno entornoBackend = BackendEntorno.localhost;

  static String get urlBaseApi {
    switch (entornoBackend) {
      case BackendEntorno.localhost:
        return 'http://127.0.0.1:8000';
      case BackendEntorno.androidEmulador:
        return 'http://10.0.2.2:8000';
    }
  }
}

enum BackendEntorno {
  localhost,
  androidEmulador,
}

