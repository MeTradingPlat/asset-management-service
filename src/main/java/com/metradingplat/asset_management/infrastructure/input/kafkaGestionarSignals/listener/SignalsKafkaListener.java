package com.metradingplat.asset_management.infrastructure.input.kafkaGestionarSignals.listener;

import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import com.metradingplat.asset_management.application.input.GestionarActivoCUIntPort;
import com.metradingplat.asset_management.domain.models.Activo;
import com.metradingplat.asset_management.infrastructure.input.kafkaGestionarSignals.DTOPetition.SignalDTOPeticion;
import com.metradingplat.asset_management.infrastructure.input.kafkaGestionarSignals.mappers.SignalKafkaMapper;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Component
@RequiredArgsConstructor
@Slf4j
public class SignalsKafkaListener {

    private final GestionarActivoCUIntPort objGestionarActivoCUInt;
    private final SignalKafkaMapper objMapper;

    @KafkaListener(topics = "signals", groupId = "activos-group")
    public void recibirSenal(SignalDTOPeticion command) {
        log.info("Recibida senal para symbol: {}, escaner: {}, tipo: {}", command.getSymbol(),
                command.getIdEscaner(), command.getTipoSenal());
        Activo objActivo = this.objMapper.deDTOADominio(command);
        this.objGestionarActivoCUInt.procesarSenal(objActivo);
    }
}
