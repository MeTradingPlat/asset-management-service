package com.metradingplat.asset_management.domain.usecases;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import com.metradingplat.asset_management.application.input.GestionarActivoCUIntPort;
import com.metradingplat.asset_management.application.output.FormateadorResultadosIntPort;
import com.metradingplat.asset_management.application.output.GestionarActivoGatewayIntPort;
import com.metradingplat.asset_management.domain.enums.EnumEstadoActivo;
import com.metradingplat.asset_management.domain.models.Activo;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@RequiredArgsConstructor
@Slf4j
public class GestionarActivoCUAdapter implements GestionarActivoCUIntPort {

    private final GestionarActivoGatewayIntPort objGestionarActivoGatewayIntPort;
    private final FormateadorResultadosIntPort objFormateadorResultadosIntPort;

    @Override
    public Activo procesarCambioEstado(Activo objActivo) {
        Optional<Activo> objExistente = this.objGestionarActivoGatewayIntPort
                .buscarPorSymbolYEscaner(objActivo.getSymbol(), objActivo.getIdEscaner());

        if (objExistente.isPresent()) {
            Activo objActivoExistente = objExistente.get();
            objActivoExistente.setEstado(objActivo.getEstado());
            objActivoExistente.setFechaActualizacion(LocalDateTime.now());
            objActivoExistente.setMetadatos(objActivo.getMetadatos());
            log.info("Actualizando estado del activo {} para escaner {}: {}",
                    objActivo.getSymbol(), objActivo.getIdEscaner(), objActivo.getEstado());
            return this.objGestionarActivoGatewayIntPort.guardar(objActivoExistente);
        } else {
            objActivo.setFechaDeteccion(LocalDateTime.now());
            objActivo.setFechaActualizacion(LocalDateTime.now());
            if (objActivo.getEstado() == null) {
                objActivo.setEstado(EnumEstadoActivo.ACTIVO.name());
            }
            log.info("Creando nuevo activo {} para escaner {}",
                    objActivo.getSymbol(), objActivo.getIdEscaner());
            return this.objGestionarActivoGatewayIntPort.guardar(objActivo);
        }
    }

    @Override
    public Activo procesarSenal(Activo objActivo) {
        Optional<Activo> objExistente = this.objGestionarActivoGatewayIntPort
                .buscarPorSymbolYEscaner(objActivo.getSymbol(), objActivo.getIdEscaner());

        if (objExistente.isPresent()) {
            Activo objActivoExistente = objExistente.get();
            objActivoExistente.setFechaActualizacion(LocalDateTime.now());
            objActivoExistente.setMetadatos(objActivo.getMetadatos());
            objActivoExistente.setEstado(EnumEstadoActivo.ACTIVO.name());
            return this.objGestionarActivoGatewayIntPort.guardar(objActivoExistente);
        } else {
            objActivo.setEstado(EnumEstadoActivo.ACTIVO.name());
            objActivo.setFechaDeteccion(LocalDateTime.now());
            objActivo.setFechaActualizacion(LocalDateTime.now());
            return this.objGestionarActivoGatewayIntPort.guardar(objActivo);
        }
    }

    @Override
    public List<Activo> obtenerActivosPorEscaner(Long idEscaner) {
        return this.objGestionarActivoGatewayIntPort.obtenerPorIdEscaner(idEscaner);
    }

    @Override
    public List<Activo> listar() {
        return this.objGestionarActivoGatewayIntPort.obtenerTodos();
    }

    @Override
    public Activo obtenerPorId(Long idActivo) {
        if (!this.objGestionarActivoGatewayIntPort.existePorId(idActivo)) {
            this.objFormateadorResultadosIntPort.errorEntidadNoExiste("error.activo.notFound", idActivo);
        }
        return this.objGestionarActivoGatewayIntPort.obtenerPorId(idActivo);
    }
}
