package com.metradingplat.asset_management.infrastructure.output.persistence.repositories;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.metradingplat.asset_management.infrastructure.output.persistence.entitys.ActivoEntity;

@Repository
public interface ActivoRepositoryInt extends JpaRepository<ActivoEntity, Long> {

    List<ActivoEntity> findByIdEscaner(Long idEscaner);

    Optional<ActivoEntity> findBySymbolAndIdEscaner(String symbol, Long idEscaner);

    void deleteByIdEscaner(Long idEscaner);
}
