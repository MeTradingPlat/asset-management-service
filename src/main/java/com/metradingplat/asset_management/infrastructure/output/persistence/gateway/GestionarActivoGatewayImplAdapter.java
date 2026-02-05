package com.metradingplat.asset_management.infrastructure.output.persistence.gateway;

import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.metradingplat.asset_management.application.output.GestionarActivoGatewayIntPort;
import com.metradingplat.asset_management.domain.models.Activo;
import com.metradingplat.asset_management.infrastructure.output.persistence.entitys.ActivoEntity;
import com.metradingplat.asset_management.infrastructure.output.persistence.mappers.ActivoMapperPersistencia;
import com.metradingplat.asset_management.infrastructure.output.persistence.repositories.ActivoRepositoryInt;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class GestionarActivoGatewayImplAdapter implements GestionarActivoGatewayIntPort {

    private final ActivoRepositoryInt objActivoRepository;
    private final ActivoMapperPersistencia objMapper;

    @Override
    @Transactional
    public Activo guardar(Activo objActivo) {
        ActivoEntity entity = this.objMapper.mappearDeActivoAEntity(objActivo);
        ActivoEntity saved = this.objActivoRepository.save(entity);
        return this.objMapper.mappearDeEntityAActivo(saved);
    }

    @Override
    @Transactional(readOnly = true)
    public List<Activo> obtenerPorIdEscaner(Long idEscaner) {
        List<ActivoEntity> entities = this.objActivoRepository.findByIdEscaner(idEscaner);
        return this.objMapper.mappearListaDeEntityAActivo(entities);
    }

    @Override
    @Transactional(readOnly = true)
    public List<Activo> obtenerTodos() {
        List<ActivoEntity> entities = this.objActivoRepository.findAll();
        return this.objMapper.mappearListaDeEntityAActivo(entities);
    }

    @Override
    @Transactional(readOnly = true)
    public Activo obtenerPorId(Long idActivo) {
        ActivoEntity entity = this.objActivoRepository.findById(idActivo).orElse(null);
        return entity != null ? this.objMapper.mappearDeEntityAActivo(entity) : null;
    }

    @Override
    @Transactional(readOnly = true)
    public Boolean existePorId(Long idActivo) {
        return this.objActivoRepository.existsById(idActivo);
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<Activo> buscarPorSymbolYEscaner(String symbol, Long idEscaner) {
        return this.objActivoRepository.findBySymbolAndIdEscaner(symbol, idEscaner)
                .map(this.objMapper::mappearDeEntityAActivo);
    }
}
