package com.metradingplat.asset_management.infrastructure.input.kafkaGestionarActivo.listener;

import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import com.metradingplat.asset_management.application.input.GestionarActivoCUIntPort;
import com.metradingplat.asset_management.domain.models.Activo;
import com.metradingplat.asset_management.infrastructure.input.kafkaGestionarActivo.DTOPetition.ActivoEstadoDTOPeticion;
import com.metradingplat.asset_management.infrastructure.input.kafkaGestionarActivo.mappers.ActivoKafkaMapper;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Component
@RequiredArgsConstructor
@Slf4j
public class ActivoKafkaListener {

    private final GestionarActivoCUIntPort objGestionarActivoCUInt;
    private final ActivoKafkaMapper objMapper;

    @KafkaListener(topics = "asset-state", groupId = "activos-group")
    public void recibirCambioEstadoActivo(ActivoEstadoDTOPeticion command) {
        log.info("Recibido cambio de estado para symbol: {}, escaner: {}", command.getSymbol(),
                command.getIdEscaner());
        Activo objActivo = this.objMapper.deDTOADominio(command);
        this.objGestionarActivoCUInt.procesarCambioEstado(objActivo);
    }
}
