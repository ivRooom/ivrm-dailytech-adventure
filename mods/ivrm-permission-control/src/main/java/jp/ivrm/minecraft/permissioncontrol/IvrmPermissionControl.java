package jp.ivrm.minecraft.permissioncontrol;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.TriState;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.BlockItem;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.entity.item.ItemTossEvent;
import net.neoforged.neoforge.event.entity.player.AttackEntityEvent;
import net.neoforged.neoforge.event.entity.player.ItemEntityPickupEvent;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import net.neoforged.neoforge.event.level.BlockEvent;
import net.neoforged.neoforge.server.permission.PermissionAPI;
import net.neoforged.neoforge.server.permission.events.PermissionGatherEvent;
import net.neoforged.neoforge.server.permission.nodes.PermissionNode;
import net.neoforged.neoforge.server.permission.nodes.PermissionTypes;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Mod(IvrmPermissionControl.MOD_ID)
public final class IvrmPermissionControl {
    public static final String MOD_ID = "ivrm_permission_control";
    private static final String PERMISSION_NAMESPACE = "ivrm";
    private static final Logger LOGGER = LoggerFactory.getLogger(IvrmPermissionControl.class);
    private static final long MESSAGE_COOLDOWN_MILLIS = 3_000L;
    private static final Component DENIED = Component.literal("この操作はメンバー承認後に利用できます。");
    private static final Map<UUID, Long> LAST_MESSAGE = new ConcurrentHashMap<>();

    public static final PermissionNode<Boolean> BUILD = permission("play.build");
    public static final PermissionNode<Boolean> CRAFT = permission("play.craft");
    public static final PermissionNode<Boolean> CONTAINER = permission("play.container");
    public static final PermissionNode<Boolean> INTERACT = permission("play.interact");
    public static final PermissionNode<Boolean> COMBAT = permission("play.combat");
    public static final PermissionNode<Boolean> PICKUP = permission("play.pickup");

    public IvrmPermissionControl() {
        NeoForge.EVENT_BUS.register(this);
        LOGGER.info("IVRM Permission Controlを初期化しました（NeoForge EVENT_BUS方式）");
    }

    private static PermissionNode<Boolean> permission(String node) {
        return new PermissionNode<>(PERMISSION_NAMESPACE, node, PermissionTypes.BOOLEAN,
                (player, playerUuid, context) -> false);
    }

    @SubscribeEvent
    public void registerPermissionNodes(PermissionGatherEvent.Nodes event) {
        event.addNodes(BUILD, CRAFT, CONTAINER, INTERACT, COMBAT, PICKUP);
        LOGGER.info("IVRM権限ノードを登録しました: {}, {}, {}, {}, {}, {}",
                BUILD.getNodeName(), CRAFT.getNodeName(), CONTAINER.getNodeName(),
                INTERACT.getNodeName(), COMBAT.getNodeName(), PICKUP.getNodeName());
    }

    @SubscribeEvent
    public void onPlace(BlockEvent.EntityPlaceEvent event) {
        if (event.getEntity() instanceof ServerPlayer player) {
            LOGGER.info("IVRMイベント検知: place player={}", player.getGameProfile().name());
            if (deny(player, BUILD)) {
                event.setCanceled(true);
                resyncInventory(player);
            }
        }
    }

    @SubscribeEvent
    public void onLeftClickBlock(PlayerInteractEvent.LeftClickBlock event) {
        ServerPlayer player = serverPlayer(event.getEntity());
        if (player != null) {
            LOGGER.info("IVRMイベント検知: left_click_block player={}", player.getGameProfile().name());
            if (deny(player, BUILD)) {
                event.setCanceled(true);
            }
        }
    }

    @SubscribeEvent
    public void onRightClickBlock(PlayerInteractEvent.RightClickBlock event) {
        ServerPlayer player = serverPlayer(event.getEntity());
        if (player == null) {
            return;
        }

        boolean placingBlock = event.getItemStack().getItem() instanceof BlockItem;
        PermissionNode<Boolean> requiredNode = placingBlock ? BUILD : INTERACT;

        LOGGER.info("IVRMイベント検知: right_click_block player={}, placing_block={}",
                player.getGameProfile().name(), placingBlock);

        if (deny(player, requiredNode)) {
            event.setCanceled(true);
            resyncInventory(player);
        }
    }

    @SubscribeEvent
    public void onRightClickItem(PlayerInteractEvent.RightClickItem event) {
        ServerPlayer player = serverPlayer(event.getEntity());
        if (player != null) {
            LOGGER.info("IVRMイベント検知: right_click_item player={}", player.getGameProfile().name());
            if (deny(player, INTERACT)) {
                event.setCanceled(true);
                resyncInventory(player);
            }
        }
    }

    @SubscribeEvent
    public void onEntityInteract(PlayerInteractEvent.EntityInteract event) {
        ServerPlayer player = serverPlayer(event.getEntity());
        if (player != null) {
            LOGGER.info("IVRMイベント検知: entity_interact player={}", player.getGameProfile().name());
            if (deny(player, INTERACT)) {
                event.setCanceled(true);
            }
        }
    }

    @SubscribeEvent
    public void onEntityInteractSpecific(PlayerInteractEvent.EntityInteractSpecific event) {
        ServerPlayer player = serverPlayer(event.getEntity());
        if (player != null) {
            LOGGER.info("IVRMイベント検知: entity_interact_specific player={}", player.getGameProfile().name());
            if (deny(player, INTERACT)) {
                event.setCanceled(true);
            }
        }
    }

    @SubscribeEvent
    public void onAttack(AttackEntityEvent event) {
        ServerPlayer player = serverPlayer(event.getEntity());
        if (player != null) {
            LOGGER.info("IVRMイベント検知: attack player={}", player.getGameProfile().name());
            if (deny(player, COMBAT)) {
                event.setCanceled(true);
            }
        }
    }

    @SubscribeEvent
    public void onPickup(ItemEntityPickupEvent.Pre event) {
        ServerPlayer player = serverPlayer(event.getPlayer());
        if (player != null) {
            LOGGER.info("IVRMイベント検知: pickup player={}", player.getGameProfile().name());
            if (deny(player, PICKUP)) {
                event.setCanPickup(TriState.FALSE);
            }
        }
    }

    @SubscribeEvent
    public void onToss(ItemTossEvent event) {
        ServerPlayer player = serverPlayer(event.getPlayer());
        if (player != null) {
            LOGGER.info("IVRMイベント検知: toss player={}", player.getGameProfile().name());
            if (deny(player, PICKUP)) {
                event.setCanceled(true);
                resyncInventory(player);
            }
        }
    }

    private static ServerPlayer serverPlayer(Player player) {
        return player instanceof ServerPlayer serverPlayer ? serverPlayer : null;
    }

    private static boolean deny(ServerPlayer player, PermissionNode<Boolean> node) {
        boolean allowed;
        try {
            allowed = PermissionAPI.getPermission(player, node);
            LOGGER.info("IVRM権限判定: player={}, node={}, allowed={}",
                    player.getGameProfile().name(), node.getNodeName(), allowed);
        } catch (RuntimeException exception) {
            LOGGER.error("権限判定に失敗したため安全側で拒否します: player={}, node={}",
                    player.getGameProfile().name(), node.getNodeName(), exception);
            allowed = false;
        }

        if (!allowed) {
            notifyDenied(player);
        }
        return !allowed;
    }

    private static void resyncInventory(ServerPlayer player) {
        player.containerMenu.sendAllDataToRemote();
        if (player.inventoryMenu != player.containerMenu) {
            player.inventoryMenu.sendAllDataToRemote();
        }
    }

    private static void notifyDenied(ServerPlayer player) {
        long now = System.currentTimeMillis();
        Long previous = LAST_MESSAGE.put(player.getUUID(), now);
        if (previous == null || now - previous >= MESSAGE_COOLDOWN_MILLIS) {
            player.sendSystemMessage(DENIED);
        }
    }
}
