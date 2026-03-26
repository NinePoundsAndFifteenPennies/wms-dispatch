<template>
  <el-card shadow="never" class="map-card">
    <template #header>
      <div class="map-card-header">
        <span>仓库地图</span>
        <el-tag type="info" effect="plain">已定位 {{ validWarehouses.length }} / {{ warehouses.length }}</el-tag>
      </div>
    </template>
    <div ref="mapRef" class="warehouse-map" />
    <p class="map-tip">底图来源：OpenStreetMap，鼠标悬浮标记可查看仓库信息。</p>
  </el-card>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import warehouseBadgeImage from '../../assets/images/warehouse-badge.svg'

const props = defineProps({
  warehouses: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['marker-click'])

const mapRef = ref(null)
let mapInstance = null
let markersLayer = null

const validWarehouses = computed(() => {
  return props.warehouses.filter((item) => {
    const lat = Number(item.latitude)
    const lng = Number(item.longitude)
    return Number.isFinite(lat) && Number.isFinite(lng)
  })
})

function buildPopupContent(warehouse) {
  const wrapper = document.createElement('div')
  wrapper.className = 'map-tooltip-card'

  const coverWrap = document.createElement('div')
  coverWrap.className = 'map-tooltip-cover'

  const coverImageUrl = resolveCoverImageUrl(warehouse.cover_image)

  if (coverImageUrl) {
    const cover = document.createElement('img')
    cover.className = 'map-tooltip-image'
    cover.src = coverImageUrl
    cover.alt = warehouse.name || 'warehouse'
    cover.loading = 'lazy'
    coverWrap.appendChild(cover)
  } else {
    const placeholder = document.createElement('div')
    placeholder.className = 'map-tooltip-image-placeholder'

    const icon = document.createElement('img')
    icon.className = 'map-tooltip-image-icon'
    icon.src = warehouseBadgeImage
    icon.alt = 'warehouse'

    const label = document.createElement('span')
    label.textContent = '暂无图片'

    placeholder.appendChild(icon)
    placeholder.appendChild(label)
    coverWrap.appendChild(placeholder)
  }

  const title = document.createElement('div')
  title.className = 'map-tooltip-title'
  title.textContent = warehouse.name || '-'

  const address = document.createElement('div')
  address.textContent = `地址：${warehouse.address || '-'}`

  const capacity = document.createElement('div')
  capacity.textContent = `容量：${warehouse.capacity ?? '-'}`

  wrapper.appendChild(coverWrap)
  wrapper.appendChild(title)
  wrapper.appendChild(address)
  wrapper.appendChild(capacity)
  return wrapper
}

function resolveCoverImageUrl(rawUrl) {
  if (!rawUrl || typeof rawUrl !== 'string') return ''
  if (/^https?:\/\//i.test(rawUrl)) return rawUrl
  if (rawUrl.startsWith('//')) return `${window.location.protocol}${rawUrl}`
  if (rawUrl.startsWith('/')) return rawUrl
  return `/${rawUrl}`
}

function escapeHtmlAttr(text) {
  return String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function createMarkerIcon(warehouse) {
  const coverImageUrl = resolveCoverImageUrl(warehouse.cover_image)

  if (coverImageUrl) {
    const safeUrl = escapeHtmlAttr(coverImageUrl)
    const safeName = escapeHtmlAttr(warehouse.name || 'warehouse')
    return L.divIcon({
      className: 'warehouse-marker-wrapper',
      html: `<div class="warehouse-marker warehouse-marker-image"><img src="${safeUrl}" alt="${safeName}"></div>`,
      iconSize: [36, 36],
      iconAnchor: [18, 36],
      tooltipAnchor: [0, -32],
    })
  }

  return L.divIcon({
    className: 'warehouse-marker-wrapper',
    html: `<div class="warehouse-marker warehouse-marker-fallback"><img src="${warehouseBadgeImage}" alt="warehouse"></div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 36],
    tooltipAnchor: [0, -32],
  })
}

function ensureMap() {
  if (mapInstance || !mapRef.value) return

  mapInstance = L.map(mapRef.value, {
    center: [35.8617, 104.1954],
    zoom: 4,
    zoomControl: true,
  })

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(mapInstance)

  markersLayer = L.layerGroup().addTo(mapInstance)
}

function renderMarkers() {
  if (!mapInstance || !markersLayer) return

  markersLayer.clearLayers()

  const bounds = []
  validWarehouses.value.forEach((warehouse) => {
    const lat = Number(warehouse.latitude)
    const lng = Number(warehouse.longitude)
    const marker = L.marker([lat, lng], {
      title: warehouse.name || 'warehouse',
      icon: createMarkerIcon(warehouse),
    }).addTo(markersLayer)

    marker.bindTooltip(buildPopupContent(warehouse), {
      permanent: false,
      sticky: true,
      direction: 'top',
      offset: [0, -34],
      opacity: 1,
      className: 'warehouse-float-tip',
    })
    marker.on('click', () => emit('marker-click', warehouse))
    bounds.push([lat, lng])
  })

  if (bounds.length === 1) {
    mapInstance.setView(bounds[0], 12)
  } else if (bounds.length > 1) {
    mapInstance.fitBounds(bounds, { padding: [24, 24] })
  } else {
    mapInstance.setView([35.8617, 104.1954], 4)
  }
}

async function initialize() {
  await nextTick()
  ensureMap()
  renderMarkers()
  if (mapInstance) {
    setTimeout(() => mapInstance?.invalidateSize(), 0)
  }
}

onMounted(() => {
  initialize()
})

watch(
  () => props.warehouses,
  async () => {
    await initialize()
  },
  { deep: true },
)

onBeforeUnmount(() => {
  if (mapInstance) {
    mapInstance.remove()
  }
  mapInstance = null
  markersLayer = null
})
</script>

<style scoped>
.map-card {
  border-radius: 12px;
}

.map-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.warehouse-map {
  width: 100%;
  height: 360px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #d8e1eb;
}

.map-tip {
  margin: 10px 0 0;
  font-size: 12px;
  color: #64748b;
}

:deep(.map-tooltip-card) {
  font-size: 12px;
  line-height: 1.5;
  min-width: 190px;
}

:deep(.warehouse-float-tip) {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0;
  color: inherit;
}

:deep(.warehouse-float-tip:before) {
  display: none;
}

:deep(.map-tooltip-cover) {
  margin-bottom: 6px;
}

:deep(.map-tooltip-image) {
  width: 100%;
  height: 88px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #d8e1eb;
}

:deep(.map-tooltip-image-placeholder) {
  width: 100%;
  height: 88px;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
  background: #f8fbff;
  color: #64748b;
  display: grid;
  place-items: center;
  gap: 2px;
}

:deep(.map-tooltip-image-icon) {
  width: 28px;
  height: 28px;
  object-fit: contain;
}

:deep(.map-tooltip-title) {
  font-weight: 700;
  margin-bottom: 2px;
}

:deep(.warehouse-marker-wrapper) {
  background: transparent;
  border: none;
}

:deep(.warehouse-marker) {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  border: 2px solid #ffffff;
  box-shadow: 0 3px 10px rgba(15, 23, 42, 0.26);
  background: #ffffff;
  overflow: hidden;
  display: grid;
  place-items: center;
}

:deep(.warehouse-marker-image img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

:deep(.warehouse-marker-fallback) {
  background: #f3f8ff;
}

:deep(.warehouse-marker-fallback img) {
  width: 22px;
  height: 22px;
  object-fit: contain;
}

@media (max-width: 980px) {
  .warehouse-map {
    height: 300px;
  }
}
</style>